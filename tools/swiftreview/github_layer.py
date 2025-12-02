import json
import os
import requests
from groq_llm import GroqLLM
from review_pipeline import process_review

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


def github_api(url):
    """Helper to call GitHub API with correct headers."""
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    return requests.get(url, headers=headers)


def get_pr_diff(owner, repo, pr_number):
    """Fetch PR diff using GitHub REST API."""

    diff_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.patch"   # IMPORTANT
    }

    r = requests.get(diff_url, headers=headers)

    if r.status_code != 200:
        raise RuntimeError(f"GitHub diff fetch failed: {r.text}")

    diff = r.text

    if not diff or diff.strip() == "":
        raise RuntimeError("GitHub returned an EMPTY DIFF.")

    return diff


def main(event_path):
    print("Loading GitHub event payload...")
    with open(event_path, "r") as f:
        payload = json.load(f)

    if "pull_request" not in payload:
        raise RuntimeError("Not a pull_request event")

    pr = payload["pull_request"]
    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pr_number = pr["number"]

    print(f"Fetching PR diff for #{pr_number}")
    diff = get_pr_diff(owner, repo, pr_number)

    print("Running review...")
    llm = GroqLLM()
    final_comment = process_review(diff, llm)

    # POST comment back to GitHub
    comment_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.post(comment_url, headers=headers, json={"body": final_comment})

    if response.status_code not in (200, 201):
        raise RuntimeError(f"Failed to post comment: {response.text}")

    print("Review posted successfully.")




# """
# GitHub Layer for SwiftReview AI
# --------------------------------
# Responsibilities:
# - Receive PR metadata from GitHub Actions env
# - Fetch changed files
# - Fetch diffs/patches
# - Filter Swift files
# - Post AI-generated review comments back to PR
# """

# import os
# import requests
# import time
# from swiftreview_groq_ai import review_pr_with_llm, format_github_review_comments

# # --- GitHub Config ---
# GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
# REPO = os.getenv("REPO")
# PR_NUMBER = int(os.getenv("PR_NUMBER"))
# API_BASE = "https://api.github.com"


# # --------------------------
# # Helper: GitHub API Headers
# # --------------------------
# def gh_headers():
#     return {
#         "Authorization": f"Bearer {GITHUB_TOKEN}",
#         "Accept": "application/vnd.github+json",
#         "X-GitHub-Api-Version": "2022-11-28"
#     }


# # ----------------------------
# # GitHub API Request Wrapper
# # ----------------------------
# def github_get(url):
#     for attempt in range(3):
#         res = requests.get(url, headers=gh_headers())
#         if res.status_code == 403 and "rate limit" in res.text.lower():
#             wait = 2 ** attempt
#             print(f"Rate limit hit. Retrying in {wait}s...")
#             time.sleep(wait)
#             continue
#         if res.status_code >= 300:
#             raise Exception(f"GitHub GET failed {res.status_code}: {res.text}")
#         return res.json()
#     raise Exception("GitHub GET failed after retries")


# def github_post(url, payload):
#     res = requests.post(url, json=payload, headers=gh_headers())
#     if res.status_code >= 300:
#         print("GitHub POST Error:", res.text)
#     return res.json()


# # ----------------------------------
# # Step 1: Fetch PR Changed File List
# # ----------------------------------
# def fetch_changed_files():
#     url = f"{API_BASE}/repos/{REPO}/pulls/{PR_NUMBER}/files"
#     return github_get(url)


# # -------------------------------------------
# # Step 2: Extract Only Swift Diffs (.swift)
# # -------------------------------------------
# def extract_swift_diffs(files_json):
#     diffs = []
#     file_paths = []

#     for f in files_json:
#         path = f.get("filename")
#         if not path.endswith(".swift"):
#             continue

#         patch = f.get("patch")     # GitHub returns unified diff
#         if not patch:
#             continue

#         diff_text = f"--- {path}\n{patch}"
#         diffs.append(diff_text)
#         file_paths.append(path)

#     return "\n\n".join(diffs), file_paths


# # -------------------------------------
# # Step 3: Post Review Comment to GitHub
# # -------------------------------------
# def post_review_comment(body, file_path, line):
#     """
#     Creates a single inline PR review comment.
#     Uses the GitHub Pull Request Review API.
#     """
#     url = f"{API_BASE}/repos/{REPO}/pulls/{PR_NUMBER}/comments"

#     payload = {
#         "body": body,
#         "path": file_path,
#         "line": line,
#         "side": "RIGHT"
#     }

#     return github_post(url, payload)


# # -------------------------------
# # MAIN EXECUTION PIPELINE
# # -------------------------------
# def main():
#     print(f"🔍 SwiftReview AI running on {REPO} | PR #{PR_NUMBER}")

#     # Fetch PR files
#     pr_files = fetch_changed_files()

#     # Extract Swift-specific diffs
#     diff_snippets, swift_files = extract_swift_diffs(pr_files)
#     if not swift_files:
#         print("No Swift file changes in this PR. Exiting.")
#         return

#     # Run LLM engine
#     parsed_json = review_pr_with_llm(
#         repo=REPO,
#         pr_number=PR_NUMBER,
#         file_list=swift_files,
#         diff_snippets=diff_snippets,
#         context_notes="Automated PR Review for Swift Code"
#     )

#     # Convert to GitHub review comment structures
#     comments = format_github_review_comments(parsed_json)

#     # Post comments back to PR
#     for c in comments:
#         line = c["end_line"] or c["start_line"]
#         post_review_comment(
#             body=c["body"],
#             file_path=c["path"],
#             line=line
#         )

#     print("✅ SwiftReview AI completed successfully.")


if __name__ == "__main__":
    main()
