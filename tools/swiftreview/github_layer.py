"""
GitHub Layer for SwiftReview AI
--------------------------------
✔ Handles PR diff & file fetching (with pagination)
✔ Fetches raw file contents for newly added files
✔ Handles rate-limits & retry logic
✔ PEP-8 compliant and no global state
✔ Provides merge-block logic based on LLM "risk" score
"""

import json
import os
import time
import logging
import requests
from typing import Dict, Any, List

from groq_llm import GroqLLM
from review_pipeline import process_review


# -----------------------------------------------------------
# Logging
# -----------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="SWIFTREVIEW: %(message)s")
log = logging.getLogger("SwiftReview")


# -----------------------------------------------------------
# GitHub API Client
# -----------------------------------------------------------
class GitHubClient:
    """Robust GitHub API wrapper with pagination and rate-limit handling."""

    def __init__(self, token: str):
        if not token:
            raise RuntimeError("Missing GITHUB_TOKEN")

        self.session = requests.Session()
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def split_into_chunks(text: str, max_chars: int = 15000) -> list:
        """Split large review input into safe-sized chunks for Groq."""
        chunks = []
        while len(text) > max_chars:
            split_point = text.rfind("\n", 0, max_chars)
            if split_point == -1:
                split_point = max_chars
            chunks.append(text[:split_point])
            text = text[split_point:]
        chunks.append(text)
        return chunks
        
    # ------------------------------------------
    # Safe GET request (retry + rate-limit)
    # ------------------------------------------
    def get(self, url: str, extra_headers: Dict[str, str] = None, retries: int = 5) -> requests.Response:
        headers = {**self.headers, **(extra_headers or {})}

        for attempt in range(1, retries + 1):
            try:
                response = self.session.get(url, headers=headers, timeout=10)
            except requests.exceptions.RequestException as e:
                log.warning(f"Network error on attempt {attempt}/{retries}: {e}")
                time.sleep(1.5)
                continue

            # Handle rate-limit (403 + X-RateLimit-Remaining = 0)
            if (
                response.status_code == 403 and
                response.headers.get("X-RateLimit-Remaining") == "0"
            ):
                wait = int(response.headers.get("Retry-After", "5"))
                log.warning(f"Rate limited. Waiting {wait}s before retry...")
                time.sleep(wait)
                continue

            # Success
            if 200 <= response.status_code < 300:
                return response

            log.warning(f"GitHub API error {response.status_code}. Retry {attempt}/{retries}")
            time.sleep(1.3)

        raise RuntimeError(f"GitHub GET failed after retries. Last response: {response.text}")

    # ------------------------------------------
    # Get ALL PR files (pagination)
    # ------------------------------------------
    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        log.info(f"Fetching PR files for PR #{pr_number}…")

        page = 1
        per_page = 100
        all_files = []

        while True:
            url = (
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
                f"?page={page}&per_page={per_page}"
            )

            response = self.get(url)
            batch = response.json()

            if not isinstance(batch, list):
                raise RuntimeError(f"Invalid GitHub response for PR files: {batch}")

            all_files.extend(batch)

            if len(batch) < per_page:
                break

            page += 1

        log.info(f"Total files retrieved: {len(all_files)}")
        return all_files

    # ------------------------------------------
    # Get PR diff as patch
    # ------------------------------------------
    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        log.info("Fetching PR diff…")

        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {"Accept": "application/vnd.github.v3.patch"}

        response = self.get(url, extra_headers=headers)
        diff = response.text or ""

        if not diff.strip():
            log.warning("Empty diff received — will fall back to raw files.")

        return diff

    # ------------------------------------------
    # Get raw file source
    # ------------------------------------------
    def get_raw_file(self, raw_url: str) -> str:
        response = self.get(raw_url)
        content = response.text or ""
        return content if content.strip() else "// Empty or binary file."

    # ------------------------------------------
    # Post PR comment
    # ------------------------------------------
    def post_comment(self, owner: str, repo: str, pr_number: int, body: str):
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"

        response = self.session.post(url, headers=self.headers, json={"body": body}, timeout=10)
        if response.status_code not in (200, 201):
            raise RuntimeError(f"Failed to post PR comment: {response.status_code}\n{response.text}")

        return response.json()


# -----------------------------------------------------------
# Build combined input for LLM (diff + raw files + patches)
# -----------------------------------------------------------
def build_review_content(gh: GitHubClient, owner: str, repo: str, pr_number: int) -> str:
    diff_text = gh.get_pr_diff(owner, repo, pr_number)
    files = gh.get_pr_files(owner, repo, pr_number)

    combined = diff_text + "\n\n### FULL FILE CONTENTS FOR ANALYSIS ###\n"

    for f in files:
        filename = f.get("filename")
        status = f.get("status")
        raw_url = f.get("raw_url")
        patch = f.get("patch")

        combined += f"\n\n--- FILE: {filename} (status: {status}) ---\n"

        # Add raw file content
        if raw_url:
            try:
                combined += gh.get_raw_file(raw_url)
            except Exception as e:
                combined += f"// Failed to load raw file: {e}\n"

        # Add patch/diff content
        if patch:
            combined += f"\n--- PATCH FOR {filename} ---\n{patch}\n"

    return combined


# -----------------------------------------------------------
# Entry Point — Called from event_handler.py
# -----------------------------------------------------------
def run_from_event_path(event_path: str):
    if not os.path.exists(event_path):
        raise RuntimeError(f"GitHub event file not found: {event_path}")

    payload = json.load(open(event_path))

    if "pull_request" not in payload:
        raise RuntimeError("This event is not a pull_request event.")

    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pr_number = payload["pull_request"]["number"]

    github_token = os.getenv("GITHUB_TOKEN")
    gh = GitHubClient(github_token)

    log.info(f"Preparing SwiftReview AI analysis for PR #{pr_number}…")

    # Build input
    review_input = build_review_content(gh, owner, repo, pr_number)

    # Run LLM
    llm = GroqLLM()
    chunks = split_into_chunks(review_input, max_chars=9000)

    combined_review = {
        "summary": "",
        "major_issues": [],
        "minor_issues": [],
        "suggestions": [],
        "risk": 0,
        "final_comment": ""
    }

    for idx, chunk in enumerate(chunks, start=1):
        log.info(f"Processing chunk {idx}/{len(chunks)}...")
        partial = process_review(chunk, llm)

        # merge summaries
        combined_review["summary"] += f"\n\n[Chunk {idx} Summary]\n" + partial["markdown"]

        # merge lists
        combined_review["major_issues"].extend(partial.get("major_issues", []))
        combined_review["minor_issues"].extend(partial.get("minor_issues", []))
        combined_review["suggestions"].extend(partial.get("suggestions", []))

        # update risk (take max, better safety)
        combined_review["risk"] = max(combined_review["risk"], partial.get("risk", 0))

    # Now we have a merged review
    review = {
        "markdown": combined_review["summary"],
        "risk": combined_review["risk"]
    }


    # Post review comment
    gh.post_comment(owner, repo, pr_number, review["markdown"])

    # Merge block rule: risk < 8
    risk = review.get("risk", 0)

    if risk < 8:
        log.error(f"❌ Risk score {risk} < 8 — merge blocked.")
        raise SystemExit(1)

    log.info(f"✅ Risk score {risk} >= 8 — merge allowed.")
