# swiftreview_ai.py

"""
swiftreview_ai.py
Lightweight LLM pipeline for SwiftReview AI (PR reviewer for iOS projects).

Requirements:
  pip install openai    # or latest OpenAI Python package that exposes `OpenAI` client
  (Alternatively use your project's HTTP client if you prefer)

Notes:
 - Replace placeholders for get_pr_diff, post_github_review_comment with your own implementations.
 - Keep secrets out of prompts. Use environment variables for API keys.
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
from groq_llm import GroqLLM

# # Use modern OpenAI client style
# try:
#     from openai import OpenAI
# except Exception:
#     # fallback import for older library naming, but prefer modern client
#     import openai as _openai
#     class OpenAI:
#         def __init__(self, api_key=None, **kw):
#             _openai.api_key = api_key or os.getenv("OPENAI_API_KEY")
#         def chat(self): raise RuntimeError("Please install modern openai package")


# ---------------------------
# Config
# ---------------------------
MODEL = os.getenv("SR_MODEL", "gpt-4o")                # change to your preferred model
TEMPERATURE = float(os.getenv("SR_TEMPERATURE", "0.0"))
MAX_TOKENS = int(os.getenv("SR_MAX_TOKENS", "1500"))
API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# llm = OpenAI(api_key=API_KEY)

# ---------------------------
# Prompt templates
# ---------------------------

SYSTEM_PROMPT = """
You are SwiftReview — an automated code reviewer specialized in Swift/iOS code.
Produce a JSON response (exactly parseable) describing issues, severity (low/medium/high),
a short summary, and suggested fixes. For each issue provide:
 - file_path
 - range: {start_line, end_line}
 - issue_id (short string)
 - title
 - explanation
 - suggested_fix (optional code or suggested changes)
 - severity ("low"|"medium"|"high")
Return ONLY a single JSON object, nothing else.
"""

USER_PROMPT_TEMPLATE = """
Repository: {repo}
Pull request: {pr_number}
Files changed: {file_list}

Context:
{context_notes}

Relevant diff (or file content snippets):
{diff_snippets}

Instructions:
1) Identify Swift-specific issues (Swift best practices, concurrency, memory, strong/weak capture,
   unused variables, force-unwrapping, SwiftLint rules, API misuse, missing tests).
2) Provide at most 10 issues prioritized by severity.
3) For each issue provide a suggested code snippet or exact text to post as a PR comment.

Output JSON schema:
{{
  "summary": "short summary",
  "issues": [
    {{
      "issue_id":"SR-1",
      "file_path": "Sources/Feature/ViewController.swift",
      "range": {{ "start_line": 10, "end_line": 15 }},
      "title":"Avoid force-unwrapping optionals",
      "explanation":"Why it's a problem and impact",
      "suggested_fix":"Suggested short code patch or text",
      "severity":"high"
    }},
    ...
  ]
}}
"""

# ---------------------------
# Utilities
# ---------------------------

def build_user_prompt(repo: str, pr_number: int, file_list: List[str],
                      diff_snippets: str, context_notes: str = "") -> str:
    return USER_PROMPT_TEMPLATE.format(
        repo=repo,
        pr_number=pr_number,
        file_list=", ".join(file_list),
        diff_snippets=diff_snippets,
        context_notes=context_notes
    )

# ---------------------------
# LLM call
# ---------------------------

# def call_llm(messages: List[Dict[str, str]],
#              model: str = MODEL,
#              temperature: float = TEMPERATURE,
#              max_tokens: int = MAX_TOKENS,
#              retries: int = 2,
#              backoff: float = 1.0) -> Dict[str, Any]:
#     """
#     Call the model, retry on transient errors.
#     Returns the assistant message (dict with 'content' string).
#     """
#     last_exc = None
#     for attempt in range(retries + 1):
#         try:
#             # modern client: client.chat.completions.create(...)
#             resp = llm.chat.completions.create(
#                 model=model,
#                 messages=messages,
#                 temperature=temperature,
#                 max_tokens=max_tokens,
#             )
#             # grab the text from the first choice
#             msg = resp.choices[0].message
#             # msg typically is a dict with "role" and "content"
#             return msg
#         except Exception as e:
#             last_exc = e
#             time.sleep(backoff * (2 ** attempt))
#     raise RuntimeError(f"LLM call failed after retries: {last_exc}")
# ---------------------------
# GROQ LLM call
# ---------------------------
def call_groq_llm(diff, repo="Unknown", pr_number="Unknown", file_list="Unknown", context_notes="None"):
    # Compose the user prompt as in USER_PROMPT_TEMPLATE
    user_prompt = USER_PROMPT_TEMPLATE.format(
        repo=repo,
        pr_number=pr_number,
        file_list=file_list,
        context_notes=context_notes,
        diff_snippets=diff
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]
    groq_client_llm = GroqLLM(api_key=GROQ_API_KEY)

    messages = [
        {"role": "system", "content": "You are SwiftReview AI"},
        {"role": "user", "content": "Review this PR diff: ..."}
    ]

    result = groq_client_llm.chat(messages)
    print("LLM Response: ",result)

# ---------------------------
# Parse JSON output safely
# ---------------------------

def parse_llm_json_response(message_content: str) -> Dict[str, Any]:
    """
    The model is asked to output raw JSON. We try to parse robustly.
    If model outputs markdown or text around JSON we try to extract JSON block.
    """
    text = message_content.strip()
    # find first { and last } to extract largest JSON-ish block
    first = text.find('{')
    last = text.rfind('}')
    if first != -1 and last != -1 and last > first:
        candidate = text[first:last+1]
    else:
        candidate = text
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # fallback: try to be resilient by replacing single quotes, trailing commas, etc.
        try:
            cand2 = candidate.replace("'", "\"")
            # naive removal of trailing commas
            cand2 = cand2.replace(",}", "}").replace(",]", "]")
            return json.loads(cand2)
        except Exception as e:
            raise ValueError(f"Failed to parse JSON from model output: {e}\nRaw: {message_content[:1000]}")

# ---------------------------
# High-level review flow
# ---------------------------

# def review_pr_with_llm(repo: str, pr_number: int, file_list: List[str],
#                        diff_snippets: str, context_notes: str = "") -> Dict[str, Any]:
def review_pr_with_llm(diff, llm="Unknown", repo="Unknown", pr_number="Unknown", file_list="Unknown", context_notes="None"):    
    """
    Main entrypoint: builds prompts, calls LLM, returns structured issues.
    """
    system_msg = {"role": "system", "content": SYSTEM_PROMPT}
    user_msg = {"role": "user", "content": build_user_prompt(repo, pr_number, file_list,
                                                            diff, context_notes)}
    # assistant_msg = call_llm([system_msg, user_msg])
    assistant_msg = call_groq_llm(diff)

    parsed = parse_llm_json_response(assistant_msg.get("content", ""))
    return parsed

# ---------------------------
# GitHub comment helper (placeholder)
# ---------------------------

def format_github_review_comments(parsed_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert parsed LLM issues into GitHub review comment payloads.
    Each dict can be posted via the GitHub Create a review comment endpoint.
    """
    comments = []
    issues = parsed_json.get("issues", [])
    for issue in issues:
        comment = {
            "path": issue.get("file_path"),
            "start_line": issue.get("range", {}).get("start_line"),
            "end_line": issue.get("range", {}).get("end_line"),
            "body": f"**{issue.get('title')}**\n\n{issue.get('explanation')}\n\n**Suggested fix**:\n```\n{issue.get('suggested_fix','')}\n```",
            "severity": issue.get("severity", "low"),
        }
        comments.append(comment)
    return comments

# ---------------------------
# Example usage (stub integration)
# ---------------------------

# if __name__ == "__main__":
#     # You should replace get_pr_diff() with your function that returns useful snippets or the entire diff.
#     # Example placeholders:
#     repo = "myorg/my-ios-app"
#     pr_number = 123
#     file_list = ["Sources/Feature/MyViewController.swift", "Sources/Feature/Model.swift"]

#     # For best results, include only the changed segments or up to the model token limit.
#     diff_snippets = """
#     --- a/Sources/Feature/MyViewController.swift
#     +++ b/Sources/Feature/MyViewController.swift
#     @@ -10,7 +10,9 @@
#       private func loadData() {
#     -    let data = try! api.fetch()
#     +    api.fetch { result in
#     +       switch result {
#     +       case .success(let d): self.handle(d)
#     +       case .failure(let e): print(e)
#     +       }
#     """
#     parsed = review_pr_with_llm(repo, pr_number, file_list, diff_snippets, context_notes="Run swiftlint in CI")
#     print("LLM parsed result:\n", json.dumps(parsed, indent=2))
#     comments = format_github_review_comments(parsed)
#     print("Prepared GitHub comments:", json.dumps(comments, indent=2))

#     # TODO: Call your GitHub API client to post review comments on the PR.
#     # e.g. post_github_review_comments(repo, pr_number, comments)
