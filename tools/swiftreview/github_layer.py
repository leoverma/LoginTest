import json
import os
import requests
from groq_llm import GroqLLM
from review_pipeline import process_review

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

API_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}


def github_get(url, headers=None):
    h = API_HEADERS if headers is None else headers
    r = requests.get(url, headers=h)
    r.raise_for_status()
    return r


def get_pr_files(owner, repo, pr_number):
    """Fetch metadata for every file in the PR."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
    return github_get(url).json()


def get_pr_diff(owner, repo, pr_number):
    """Fetch PR patch/diff from GitHub."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.patch"
    }

    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.text or ""


def build_review_content(owner, repo, pr_number):
    """
    Combines:
    - Diff content (patch)
    - Full source code of newly added files
    """

    diff_text = get_pr_diff(owner, repo, pr_number)
    files = get_pr_files(owner, repo, pr_number)

    result = diff_text + "\n\n### NEW FILE CONTENTS ###\n"

    for f in files:
        filename = f["filename"]
        status = f["status"]
        raw_url = f.get("raw_url")
        patch = f.get("patch")

        # 1. Include new file content
        if status == "added":
            result += f"\n\n--- NEW FILE: {filename} ---\n"
            if raw_url:
                raw = github_get(raw_url).text
                result += raw
            else:
                result += "// Unable to fetch raw file contents\n"

        # 2. If patch exists but diff was empty, include patch explicitly
        if patch:
            result += f"\n\n--- PATCH FOR {filename} ---\n"
            result += patch

    return result


def post_comment(owner, repo, pr_number, body):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    r = requests.post(url, headers=API_HEADERS, json={"body": body})
    r.raise_for_status()
    return r.json()


def run_from_event_path(event_path):
    if not os.path.exists(event_path):
        raise RuntimeError("GitHub event file not found.")

    payload = json.load(open(event_path))

    if "pull_request" not in payload:
        raise RuntimeError("Not a pull_request event.")

    pr = payload["pull_request"]
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pr_number = pr["number"]

    print(f"Building unified diff + file content for PR #{pr_number}")
    unified_input = build_review_content(owner, repo, pr_number)

    llm = GroqLLM()
    review = process_review(unified_input, llm)

    comment = review["markdown"]
    risk = review["risk"]

    post_comment(owner, repo, pr_number, comment)

    if risk < 8:
        print(f"❌ Risk {risk} < 8 → merge blocked")
        raise SystemExit(1)

    print(f"✅ Risk {risk} ≥ 8 → merge allowed")


# import json
# import os
# import requests
# from groq_llm import GroqLLM
# from review_pipeline import process_review

# GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


# def get_pr_diff(owner, repo, pr_number):
#     """Fetch PR diff using GitHub REST API."""
#     diff_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"

#     headers = {
#         "Authorization": f"Bearer {GITHUB_TOKEN}",
#         "Accept": "application/vnd.github.v3.patch"
#     }

#     try:
#         r = requests.get(diff_url, headers=headers)
#         r.raise_for_status()
#     except requests.RequestException as e:
#         raise RuntimeError(f"Failed to fetch PR diff: {e}") from e

#     diff = r.text

#     if not diff.strip():
#         raise RuntimeError("GitHub returned an empty diff. The PR may not contain code changes.")

#     return diff


# def post_comment(owner, repo, pr_number, body):
#     """Post review comment on PR."""
#     url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
#     headers = {
#         "Authorization": f"Bearer {GITHUB_TOKEN}",
#         "Accept": "application/vnd.github.v3+json"
#     }

#     try:
#         r = requests.post(url, headers=headers, json={"body": body})
#         r.raise_for_status()
#     except requests.RequestException as e:
#         raise RuntimeError(f"Failed to post PR comment: {e}") from e

#     return r.json()


# def run_from_event_path(event_path):
#     """Main entry: orchestrates diff fetch → AI review → PR comment."""
#     print(f"Reading GitHub event payload from: {event_path}")

#     if not os.path.exists(event_path):
#         raise RuntimeError(f"GitHub event file not found: {event_path}")

#     try:
#         with open(event_path, "r") as f:
#             payload = json.load(f)
#     except json.JSONDecodeError as e:
#         raise RuntimeError(f"Invalid GitHub event JSON: {e}")

#     if "pull_request" not in payload:
#         raise RuntimeError("Event is not a pull_request — SwiftReview AI only runs on PR events.")

#     pr = payload["pull_request"]
#     owner = payload["repository"]["owner"]["login"]
#     repo = payload["repository"]["name"]
#     pr_number = pr["number"]

#     print(f"Processing PR #{pr_number} from {owner}/{repo}")

#     try:
#         diff = get_pr_diff(owner, repo, pr_number)
#     except Exception as e:
#         raise RuntimeError(f"Failed to fetch PR diff: {e}")

#     llm = GroqLLM()

#     try:
#         review = process_review(diff, llm)
#     except Exception as e:
#         raise RuntimeError(f"SwiftReviewAI failed to analyze PR: {e}")

#     comment = review["markdown"]
#     risk = review["risk"]

#     try:
#         post_comment(owner, repo, pr_number, comment)
#     except Exception as e:
#         raise RuntimeError(f"Failed to post review comment: {e}")

#     # Fail build if score < 8
#     if risk < 8:
#         print(f"❌ SwiftReview AI: Risk score {risk} < 8 → merge is blocked.")
#         raise SystemExit(1)

#     print(f"✅ SwiftReview AI: Risk score {risk} ≥ 8 → merge allowed.")

