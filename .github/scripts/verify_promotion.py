import json
import os
import requests
import sys


def fail(message):
    print(message)
    sys.exit(1)


def get_json(url, token):
    response = requests.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json"
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def find_ai_review_check(check_runs):
    for check in check_runs:
        if check.get("name") == "AI Agentic Code Review":
            return check
    return None


def main():
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    deployment_sha = os.environ.get("DEPLOYMENT_SHA")
    pr_number = os.environ.get("PR_NUMBER")

    if not token or not repo:
        fail("Missing required environment variables: GITHUB_TOKEN, GITHUB_REPOSITORY")

    if deployment_sha:
        commit_url = f"https://api.github.com/repos/{repo}/commits/{deployment_sha}/check-runs"
        data = get_json(commit_url, token)
        check_run = find_ai_review_check(data.get("check_runs", []))
        if check_run is None:
            fail(f"No AI Agentic Code Review check run found for commit {deployment_sha}.")
    elif pr_number:
        check_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/check-runs"
        data = get_json(check_url, token)
        check_run = find_ai_review_check(data.get("check_runs", []))
        if check_run is None:
            fail(f"No AI Agentic Code Review check run found for PR #{pr_number}.")
        deployment_sha = check_run.get("head_sha")
    else:
        fail("Either DEPLOYMENT_SHA or PR_NUMBER input must be provided to verify AI review.")

    conclusion = check_run.get("conclusion")
    if conclusion != "success":
        fail(f"AI Agentic Code Review did not pass. Found conclusion={conclusion}.")

    report = {
        "production_deployment_sha": deployment_sha,
        "ai_review_check_name": check_run.get("name"),
        "ai_review_conclusion": conclusion,
        "ai_review_started_at": check_run.get("started_at"),
        "ai_review_completed_at": check_run.get("completed_at"),
        "pushed_by": os.environ.get("GITHUB_ACTOR"),
        "approved_via_environment": True,
        "review_reference": f"PR #{pr_number}" if pr_number else None,
    }

    with open("production-promotion-report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("Production promotion verification completed successfully.")


if __name__ == "__main__":
    main()
