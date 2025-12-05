import json


# // Very Strict review
# SYSTEM_PROMPT = """
# You are SwiftReview AI — a senior iOS reviewer trained to evaluate Swift, SwiftUI, Combine,
# UIKit, Clean Architecture, MVVM, concurrency, async/await, architecture, and testability.

# Return STRICT JSON ONLY:
# {
#   "summary": "",
#   "major_issues": [],
#   "minor_issues": [],
#   "suggestions": [],
#   "risk": 0,
#   "final_comment": ""
# }
# """


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


def process_review(diff, llm):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Review this PR diff:\n{diff}\n\nReturn STRICT JSON."}
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

    # Validate required fields
    required_fields = ["summary", "major_issues", "minor_issues", "suggestions", "risk", "final_comment"]
    for field in required_fields:
        if field not in data:
            raise RuntimeError(f"Missing required field '{field}' in LLM output.")

    return {
        "markdown": format_review_comment(data),
        "risk": data.get("risk", 0)
    }


def format_review_comment(data):
    comment = "### 🧠 SwiftReview AI — Automated PR Review\n\n"
    comment += f"#### 📌 Summary\n{data['summary']}\n\n"

    if data["major_issues"]:
        comment += "#### ❗ Major Issues\n"
        for m in data["major_issues"]:
            comment += f"- {m}\n"
        comment += "\n"

    if data["minor_issues"]:
        comment += "#### ⚠️ Minor Issues\n"
        for m in data["minor_issues"]:
            comment += f"- {m}\n"
        comment += "\n"

    if data["suggestions"]:
        comment += "#### 💡 Suggestions\n"
        for s in data["suggestions"]:
            comment += f"- {s}\n"
        comment += "\n"

    comment += f"#### 🔥 Risk Score: **{data['risk']}/10**\n\n"
    comment += "#### 📝 Final Comment\n"
    comment += data["final_comment"]

    return comment



# import json

# SYSTEM_PROMPT = """
# You are SwiftReview AI — a senior iOS reviewer trained to evaluate Swift, SwiftUI, Combine,
# UIKit, Clean Architecture, MVVM, concurrency, async/await, architecture, and testability.

# Return STRICT JSON ONLY:
# {
#   "summary": "",
#   "major_issues": [],
#   "minor_issues": [],
#   "suggestions": [],
#   "risk": 0,
#   "final_comment": ""
# }
# """

# def process_review(diff, llm):
#     messages = [
#         {"role": "system", "content": SYSTEM_PROMPT},
#         {"role": "user", "content": f"Review the following PR diff:\n\n{diff}\n\nReturn STRICT JSON."}
#     ]

#     raw = llm.chat(messages)

#     try:
#         data = json.loads(raw)
#     except Exception:
#         # fallback in case model wraps text
#         start = raw.find("{")
#         end = raw.rfind("}")
#         data = json.loads(raw[start:end+1])

#     return {
#         "markdown": format_review_comment(data),
#         "risk": data.get("risk", 0)
#     }


# def format_review_comment(data):
#     comment = "### 🧠 SwiftReview AI — Automated PR Review\n\n"

#     comment += f"#### 📌 Summary\n{data['summary']}\n\n"

#     if data["major_issues"]:
#         comment += "#### ❗ Major Issues\n"
#         for m in data["major_issues"]:
#             comment += f"- {m}\n"
#         comment += "\n"

#     if data["minor_issues"]:
#         comment += "#### ⚠️ Minor Issues\n"
#         for m in data["minor_issues"]:
#             comment += f"- {m}\n"
#         comment += "\n"

#     if data["suggestions"]:
#         comment += "#### 💡 Suggestions\n"
#         for s in data["suggestions"]:
#             comment += f"- {s}\n"
#         comment += "\n"

#     comment += f"#### 🔥 Risk Score: **{data['risk']}/10**\n\n"

#     comment += "#### 📝 Final Comment\n"
#     comment += data["final_comment"]

#     return comment
