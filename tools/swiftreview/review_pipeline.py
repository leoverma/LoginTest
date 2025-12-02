import json

SYSTEM_PROMPT = """
You are SwiftReview AI — a senior iOS reviewer trained to evaluate:
Swift, SwiftUI, Combine, UIKit, Async/Await, MVVM, Clean Architecture,
testability, SOLID, performance, security, and maintainability.

Return STRICT JSON ONLY:

{
  "summary": "",
  "major_issues": [],
  "minor_issues": [],
  "suggestions": [],
  "risk": 0,
  "final_comment": ""
}
"""


def process_review(diff, llm):
    """
    Sends a chunk of diff/file content to the LLM and returns STRICT JSON.
    We DO NOT format markdown here — this file only handles raw JSON.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Review the following PR code segment.\n\n"
                + diff +
                "\n\nReturn STRICT JSON ONLY (no markdown)."
            )
        }
    ]

    raw = llm.chat(messages)

    # Attempt direct JSON parse
    try:
        data = json.loads(raw)
        return data
    except Exception:
        # Recover even if the model adds noise
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            raise RuntimeError("LLM returned non-JSON output:\n" + raw)

        data = json.loads(raw[start:end + 1])
        return data


def format_review_comment(data):
    """
    Convert merged structured JSON into GitHub-friendly Markdown.
    Ensures one clean unified comment.
    """
    comment = "### 🧠 SwiftReview AI — Automated PR Review\n\n"

    # --- Summary ---
    comment += f"#### 📌 Summary\n{data.get('summary', '').strip()}\n\n"

    # --- Major Issues ---
    major = data.get("major_issues", [])
    if major:
        comment += "#### ❗ Major Issues\n"
        for m in major:
            comment += f"- {m}\n"
        comment += "\n"

    # --- Minor Issues ---
    minor = data.get("minor_issues", [])
    if minor:
        comment += "#### ⚠️ Minor Issues\n"
        for m in minor:
            comment += f"- {m}\n"
        comment += "\n"

    # --- Suggestions ---
    suggestions = data.get("suggestions", [])
    if suggestions:
        comment += "#### 💡 Suggestions\n"
        for s in suggestions:
            comment += f"- {s}\n"
        comment += "\n"

    # --- Risk ---
    comment += (
        f"#### 🔥 Risk Score: **{data.get('risk', 0)}/10**\n\n"
    )

    # --- Final Comment ---
    comment += "#### 📝 Final Comment\n"
    comment += data.get("final_comment", "").strip()

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
#         {"role": "user", "content": f"Review this PR diff:\n{diff}\n\nReturn STRICT JSON."}
#     ]

#     raw = llm.chat(messages)

#     if not raw or not raw.strip():
#         raise RuntimeError("LLM returned empty response.")

#     data = None

#     # Strong JSON parsing with helpful error messages
#     try:
#         data = json.loads(raw)
#     except json.JSONDecodeError:
#         try:
#             # Try extracting JSON section
#             start = raw.find("{")
#             end = raw.rfind("}")
#             if start == -1 or end == -1:
#                 raise RuntimeError("LLM output does not contain JSON.")
#             data = json.loads(raw[start:end + 1])
#         except Exception as e:
#             raise RuntimeError(f"Failed to parse JSON response from LLM. Raw output:\n{raw}") from e

#     # Validate required fields
#     required_fields = ["summary", "major_issues", "minor_issues", "suggestions", "risk", "final_comment"]
#     for field in required_fields:
#         if field not in data:
#             raise RuntimeError(f"Missing required field '{field}' in LLM output.")

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
