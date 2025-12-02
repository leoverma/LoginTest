"""
swiftreview_groq_ai.py
LLM pipeline for SwiftReview AI (GROQ-backed).
"""

import os
import json
from typing import List, Dict, Any
from groq_llm import chat as groq_chat  # local wrapper above

# Config
TEMPERATURE = float(os.getenv("SR_TEMPERATURE", "0.0"))
MAX_TOKENS = int(os.getenv("SR_MAX_TOKENS", "1500"))

SYSTEM_PROMPT = """
You are SwiftReview — an automated code reviewer specialized in Swift/iOS code.
Produce a JSON response (exactly parseable) describing issues, severity (low/medium/high),
a short summary, and suggested fixes. For each issue provide:
 - file_path
 - range: {start_line, end_line}
 - issue_id
 - title
 - explanation
 - suggested_fix
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

def build_user_prompt(repo: str, pr_number: int, file_list: List[str],
                      diff_snippets: str, context_notes: str = "") -> str:
    return USER_PROMPT_TEMPLATE.format(
        repo=repo,
        pr_number=pr_number,
        file_list=", ".join(file_list),
        diff_snippets=diff_snippets,
        context_notes=context_notes
    )

def call_groq_llm(system_prompt: str, user_prompt: str) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    return groq_chat(messages=messages, temperature=TEMPERATURE, max_tokens=MAX_TOKENS)

def parse_llm_json_response(message_content: str) -> Dict[str, Any]:
    # Extract the largest JSON object
    text = (message_content or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    candidate = text[start:end+1] if start != -1 and end != -1 and end > start else text
    try:
        return json.loads(candidate)
    except Exception:
        # best-effort cleanup
        cand2 = candidate.replace("'", "\"").replace(",}", "}").replace(",]", "]")
        return json.loads(cand2)

def review_pr_with_llm(repo: str, pr_number: int, file_list: List[str],
                       diff_snippets: str, context_notes: str = "") -> Dict[str, Any]:
    user_prompt = build_user_prompt(repo, pr_number, file_list, diff_snippets, context_notes)
    assistant_text = call_groq_llm(SYSTEM_PROMPT, user_prompt)
    parsed = parse_llm_json_response(assistant_text)
    return parsed

def format_github_review_comments(parsed_json: Dict[str, Any]) -> List[Dict[str, Any]]:
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

# # Optional local run test
# if __name__ == "__main__":
#     repo = "example/repo"
#     pr_number = 1
#     file_list = ["Sources/Example/VC.swift"]
#     diff_snippets = "+++ Sources/Example/VC.swift\n- let x = foo!\n+ let x = foo ?? default"
#     print("Running local test of swiftreview_groq_ai...")
#     print(repo, pr_number, file_list, diff_snippets)
#     parsed = review_pr_with_llm(repo, pr_number, file_list, diff_snippets, context_notes="run swiftlint")
#     print(json.dumps(parsed, indent=2))
