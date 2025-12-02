import json
import os
from github import Github
from review_pipeline import process_review
from groq_llm import GroqLLM

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

def get_pr_diff(owner, repo, pr_number, client):
    """Fetch PR diff as unified patch."""
    pr = client.get_repo(f"{owner}/{repo}").get_pull(pr_number)

    diff = pr.raw_data.get("diff_url")  # try direct diff first
    if diff:
        import requests
        r = requests.get(diff)
        if r.status_code == 200:
            return r.text

    # fallback using GitHub API
    patch = pr.raw_data.get("patch_url")
    if patch:
        r = requests.get(patch)
        if r.status_code == 200:
            return r.text

    # last fallback
    print("Warning: GitHub did not return diff or patch URL, using base comparison.")
    base = pr.base.sha
    head = pr.head.sha
    comparison = client.get_repo(f"{owner}/{repo}") \
                       .compare(base, head)
    return comparison.patch


def main(event_path):
    with open(event_path, "r") as f:
        payload = json.load(f)

    if "pull_request" not in payload:
        raise RuntimeError("Not a PR event")

    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pr_number = payload["pull_request"]["number"]

    gh = Github(GITHUB_TOKEN)

    print(f"Fetching diff for PR #{pr_number}")
    diff = get_pr_diff(owner, repo, pr_number, gh)

    if not diff or diff.strip() == "":
        raise RuntimeError(
            "GitHub returned an EMPTY DIFF — cannot review. "
            "Make sure your workflow is triggered by pull_request events."
        )

    llm = GroqLLM()

    print("Sending PR diff to Groq model...")
    review_comment = process_review(diff, llm)

    print("Posting review comment...")

    pr = gh.get_repo(f"{owner}/{repo}").get_pull(pr_number)
    pr.create_issue_comment(review_comment)

    print("Review posted successfully.")
