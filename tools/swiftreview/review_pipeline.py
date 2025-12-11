import json
import os

# def _load_prompt_file(filename):
#     with open(os.path.join(os.path.dirname(__file__), filename), 'r', encoding='utf-8') as f:
#         return f.read()

# SYSTEM_PROMPT = _load_prompt_file("swiftreview_system_prompt.txt")
# USER_PROMPT_TEMPLATE = _load_prompt_file("swiftreview_user_prompt_template.txt")

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

USER_PROMPT_TEMPLATE="""
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
}}"""

def process_review(diff, llm, repo="Unknown", pr_number="Unknown", file_list="Unknown", context_notes="None"):
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

    raw = llm.chat(messages)

    if not raw or not raw.strip():
        raise RuntimeError("LLM returned empty response.")

    data = None

    # Strong JSON parsing with helpful error messages
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        try:
            # Try extracting JSON section
            start = raw.find("{")
            end = raw.rfind("}")
            if start == -1 or end == -1:
                raise RuntimeError("LLM output does not contain JSON.")
            data = json.loads(raw[start:end + 1])
        except Exception as e:
            raise RuntimeError(f"Failed to parse JSON response from LLM. Raw output:\n{raw}") from e

    # Validate required fields as per USER_PROMPT_TEMPLATE
    required_fields = ["summary", "issues"]
    for field in required_fields:
        if field not in data:
            raise RuntimeError(f"Missing required field '{field}' in LLM output.")

    return {
        "markdown": format_review_comment_user_prompt(data),
        "risk": _highest_severity_risk(data.get("issues", []))
    }


def format_review_comment_user_prompt(data):
    comment = "### 🧠 SwiftReview AI — Automated PR Review\n\n"
    comment += f"#### 📌 Summary\n{data['summary']}\n\n"
    issues = data.get("issues", [])
    if issues:
        comment += "#### 📝 Issues\n"
        for idx, issue in enumerate(issues, 1):
            comment += (
                f"**{idx}. [{issue.get('severity','').upper()}] {issue.get('title','')}**\n"
                f"- **File:** `{issue.get('file_path','')}` (lines {issue.get('range',{}).get('start_line','?')}-{issue.get('range',{}).get('end_line','?')})\n"
                f"- **Issue ID:** `{issue.get('issue_id','')}`\n"
                f"- **Explanation:** {issue.get('explanation','')}\n"
            )
            if issue.get("suggested_fix"):
                comment += f"- **Suggested fix:**\n```\n{issue['suggested_fix']}\n```\n"
            comment += "\n"
    else:
        comment += "No issues found.\n\n"
    return comment

def _highest_severity_risk(issues):
    # Maps severity to risk score (arbitrary, can be tuned)
    sev_map = {"low": 2, "medium": 5, "high": 9}
    if not issues:
        return 0
    max_sev_num = 0
    for i in issues:
        sev = i.get("severity", "").lower()
        max_sev_num = max(max_sev_num, sev_map.get(sev, 0))
    return max_sev_num

