import json
import os
import re
import subprocess
import sys
import requests

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def safe_json_parse(text):
    text = text.strip()
    json_match = re.search(r"\{(?:.|\n)*\}", text)
    if not json_match:
        raise ValueError("No JSON object found in model response")
    return json.loads(json_match.group(0))


def build_prompt(diff_text):
    return f"""
You are a strict senior software engineer conducting an enterprise production readiness review of a change set.

Review the diff and verify the code meets the following requirements:
- No silent failures or swallowed exceptions
- Robust error handling and retry logic
- Clear logging, observability, and operational traceability
- Alerting or failure notification mechanisms for production incidents
- No hardcoded secrets or insecure credential handling
- No risky shell / subprocess execution without validation
- Secure SQL/database access and parameter handling
- No insecure default behavior or missing timeouts
- Maintainable, testable, and scalable code patterns
- Production readiness and deployment safety

Provide a defensible audit report in strict JSON ONLY with this exact shape:
{
  "status": "PASS or FAIL",
  "summary": "Short summary of findings",
  "issues": [
    {
      "severity": "LOW|MEDIUM|HIGH|CRITICAL",
      "file": "relative/path/to/file",
      "problem": "Description of the problem",
      "recommendation": "Clear remediation guidance"
    }
  ]
}

If any issue is serious or if the response cannot be expressed as valid JSON, return FAIL.

Review diff:
{diff_text}
""".strip()


def create_pr_comment(repo, pr_number, token, review):
    body = f"""
# AI Agentic Review Result

**Status:** {review['status']}

## Summary
{review.get('summary', 'No summary provided')}

## Findings
```json
{json.dumps(review, indent=2)}
```

> This review was completed automatically by the AI Agentic Code Review workflow.
"""
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }
    response = requests.post(url, headers=headers, json={"body": body}, timeout=30)
    response.raise_for_status()


if __name__ == "__main__":
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    github_token = os.environ.get("GITHUB_TOKEN")
    repo_name = os.environ.get("REPO_NAME")
    pr_number = os.environ.get("PR_NUMBER")
    base_ref = os.environ.get("BASE_REF", "main")

    if not all([openai_api_key, github_token, repo_name, pr_number]):
        raise SystemExit("Missing required environment variables: OPENAI_API_KEY, GITHUB_TOKEN, REPO_NAME, PR_NUMBER")

    diff_text, diff_err, code = run_command(f"git diff origin/{base_ref}...HEAD")
    if code != 0:
        raise SystemExit(f"Git diff failed: {diff_err}")

    if not diff_text:
        diff_text = "No diff content was detected. Review the current branch changes and verify there are no production risks."

    prompt = build_prompt(diff_text)
    payload = {
        "model": "gpt-4.1-mini",
        "temperature": 0,
        "messages": [
            {"role": "system", "content": "You are an enterprise-grade senior software engineer."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 1200
    }
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }

    response = requests.post(OPENAI_API_URL, headers=headers, json=payload, timeout=120)
    response.raise_for_status()
    model_output = response.json()
    assistant_text = model_output["choices"][0]["message"]["content"].strip()

    try:
        review = safe_json_parse(assistant_text)
    except Exception as exc:
        review = {
            "status": "FAIL",
            "summary": "AI response could not be parsed as valid JSON.",
            "issues": [
                {
                    "severity": "CRITICAL",
                    "file": "<ai-review>",
                    "problem": "AI returned invalid JSON",
                    "recommendation": str(exc)
                }
            ]
        }

    if review.get("status") not in {"PASS", "FAIL"}:
        review["status"] = "FAIL"
        review.setdefault("issues", []).append({
            "severity": "CRITICAL",
            "file": "<ai-review>",
            "problem": "Invalid status returned by AI",
            "recommendation": "Ensure the model returns PASS or FAIL in the status field"
        })

    with open("ai-review-report.json", "w", encoding="utf-8") as f:
        json.dump(review, f, indent=2)

    create_pr_comment(repo_name, pr_number, github_token, review)

    if review["status"] == "FAIL":
        raise SystemExit("AI review failed: production promotion blocked until issues are resolved.")
    print("AI review passed successfully.")
