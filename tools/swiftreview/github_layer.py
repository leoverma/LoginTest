"""
github_layer.py

Production-ready GitHub layer for SwiftReview AI with chunking support.
- Builds unified input (diff + raw files)
- Splits into safe-sized chunks for LLM requests
- Processes each chunk and merges results
- Posts a single comment and blocks merge if risk < 8
"""

import json
import os
import time
import logging
import requests
from typing import Dict, Any, List

from groq_llm import GroqLLM
from review_pipeline import process_review

# -------------------------
# Logging
# -------------------------
logging.basicConfig(level=logging.INFO, format="SWIFTREVIEW: %(message)s")
log = logging.getLogger("SwiftReview")


# -------------------------
# GitHub client
# -------------------------
class GitHubClient:
    """Small GitHub client with retries, pagination, and rate-limit handling."""

    def __init__(self, token: str):
        if not token:
            raise RuntimeError("Missing GITHUB_TOKEN")
        self.session = requests.Session()
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def get(self, url: str, extra_headers: Dict[str, str] = None, retries: int = 5) -> requests.Response:
        headers = {**self.headers, **(extra_headers or {})}
        response = None

        for attempt in range(1, retries + 1):
            try:
                response = self.session.get(url, headers=headers, timeout=10)
            except requests.exceptions.RequestException as e:
                log.warning(f"Network error on attempt {attempt}/{retries}: {e}")
                time.sleep(1.5)
                continue

            # Rate-limit handling
            if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
                wait = int(response.headers.get("Retry-After", "5"))
                log.warning(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue

            # Success path
            if 200 <= response.status_code < 300:
                return response

            # Otherwise retry
            log.warning(f"GitHub API returned {response.status_code}. Retry {attempt}/{retries}")
            time.sleep(1.2)

        # If we've exhausted retries
        body = response.text if response is not None else "<no response>"
        raise RuntimeError(f"GET {url} failed after {retries} retries. Last response: {body}")

    def get_pr_files(self, owner: str, repo: str, pr_number: int) -> List[Dict[str, Any]]:
        """Return full list of files changed in PR (handles pagination)."""
        log.info(f"Listing files for PR #{pr_number}")
        page = 1
        per_page = 100
        all_files: List[Dict[str, Any]] = []

        while True:
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files?page={page}&per_page={per_page}"
            resp = self.get(url)
            batch = resp.json()

            if not isinstance(batch, list):
                raise RuntimeError(f"Unexpected response for PR files: {batch}")

            all_files.extend(batch)
            if len(batch) < per_page:
                break
            page += 1

        log.info(f"Total files retrieved: {len(all_files)}")
        return all_files

    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Return PR diff/patch text (may be empty)."""
        log.info("Fetching PR diff (patch format)...")
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        extra_headers = {"Accept": "application/vnd.github.v3.patch"}
        resp = self.get(url, extra_headers=extra_headers)
        diff_text = resp.text or ""
        if not diff_text.strip():
            log.warning("Empty diff received from GitHub (patch). Will fallback to raw file contents.")
        return diff_text

    def get_raw_file(self, raw_url: str) -> str:
        resp = self.get(raw_url)
        text = resp.text or ""
        return text if text.strip() else "// Empty or binary file."

    def post_comment(self, owner: str, repo: str, pr_number: int, body: str):
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
        resp = self.session.post(url, headers=self.headers, json={"body": body}, timeout=10)
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Failed to post comment: {resp.status_code}\n{resp.text}")
        return resp.json()


# -------------------------
# Chunking utility
# -------------------------
def split_into_chunks(text: str, max_chars: int = 11000) -> List[str]:
    """
    Split text into chunks safely by splitting at newline boundaries when possible.
    Groq error indicated token limits; using a max_chars heuristic helps keep token size low.
    """
    chunks: List[str] = []
    remaining = text
    while len(remaining) > max_chars:
        # Prefer splitting at the last newline before max_chars
        split_point = remaining.rfind("\n", 0, max_chars)
        if split_point == -1:
            split_point = max_chars
        chunk = remaining[:split_point]
        chunks.append(chunk)
        remaining = remaining[split_point:]
    chunks.append(remaining)
    return chunks


# -------------------------
# Build input for review
# -------------------------
def build_review_content(gh: GitHubClient, owner: str, repo: str, pr_number: int) -> str:
    """Combine PR patch + raw contents of files into a single text blob for analysis."""
    diff_text = gh.get_pr_diff(owner, repo, pr_number)
    files = gh.get_pr_files(owner, repo, pr_number)

    combined = diff_text + "\n\n### FULL FILE CONTENTS FOR ANALYSIS ###\n"

    for f in files:
        filename = f.get("filename")
        status = f.get("status")
        raw_url = f.get("raw_url")
        patch = f.get("patch")

        combined += f"\n\n--- FILE: {filename} (status: {status}) ---\n"

        if raw_url:
            try:
                combined += gh.get_raw_file(raw_url)
            except Exception as e:
                combined += f"// Failed to fetch raw file: {e}\n"

        if patch:
            combined += f"\n--- PATCH FOR {filename} ---\n{patch}\n"

    return combined


# -------------------------
# Entry point used by event_handler.py
# -------------------------
def run_from_event_path(event_path: str):
    if not os.path.exists(event_path):
        raise RuntimeError(f"GitHub event file not found: {event_path}")

    log.info(f"Loading GitHub event: {event_path}")
    try:
        payload = json.load(open(event_path))
    except Exception as e:
        raise RuntimeError(f"Unable to read GitHub event JSON: {e}")

    if "pull_request" not in payload:
        raise RuntimeError("Event is not a pull_request event.")

    owner = payload["repository"]["owner"]["login"]
    repo = payload["repository"]["name"]
    pr_number = payload["pull_request"]["number"]

    github_token = os.getenv("GITHUB_TOKEN")
    gh = GitHubClient(github_token)

    log.info(f"Preparing analysis input for PR #{pr_number} in {owner}/{repo}")

    # Build the big review input (diff + files)
    review_input = build_review_content(gh, owner, repo, pr_number)

    # If the input is large, split into chunks
    chunks = split_into_chunks(review_input, max_chars=9000)
    log.info(f"Split review input into {len(chunks)} chunk(s)")

    llm = GroqLLM()

    # Process each chunk and merge results
    combined_markdown_parts: List[str] = []
    combined_risk = 0

    for idx, chunk in enumerate(chunks, start=1):
        log.info(f"Processing chunk {idx}/{len(chunks)}")
        # process_review should return a dict: {"markdown": "...", "risk": n}
        partial = process_review(chunk, llm)

        if not isinstance(partial, dict) or "markdown" not in partial:
            # Defensive: if process_review returns raw markdown, wrap it
            log.warning("process_review returned unexpected format; coercing to markdown-only result.")
            partial_markdown = str(partial)
            partial_risk = 0
        else:
            partial_markdown = partial["markdown"]
            partial_risk = int(partial.get("risk", 0))

        combined_markdown_parts.append(f"## Chunk {idx} Analysis\n\n" + partial_markdown)
        combined_risk = max(combined_risk, partial_risk)

    # Build final markdown
    final_markdown = (
        "### 🧠 SwiftReview AI — Combined PR Review\n\n"
        f"**Combined risk score (max across chunks): {combined_risk}/10**\n\n"
        + "\n\n".join(combined_markdown_parts)
    )

    # Post the combined comment
    gh.post_comment(owner, repo, pr_number, final_markdown)

    # Block merge if risk below threshold
    if combined_risk < 8:
        log.error(f"❌ SwiftReviewAI Risk Score {combined_risk} < 8 — Merge Blocked.")
        # Exit non-zero to make GitHub Action fail (and block merge if required)
        raise SystemExit(1)

    log.info(f"✅ SwiftReviewAI Risk Score {combined_risk} ≥ 8 — Merge Allowed.")
