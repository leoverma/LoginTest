import json

SYSTEM_PROMPT = """
You are SwiftReview AI — a senior iOS reviewer trained to evaluate Swift, SwiftUI, Combine,
UIKit, Clean Architecture, MVVM, concurrency, async/await, architecture, and testability.

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
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Review the following PR diff:\n\n{diff}\n\nReturn STRICT JSON."}
    ]

    raw = llm.chat(messages)

    try:
        data = json.loads(raw)
    except Exception:
        # fallback in case model wraps text
        start = raw.find("{")
        end = raw.rfind("}")
        data = json.loads(raw[start:end+1])

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
