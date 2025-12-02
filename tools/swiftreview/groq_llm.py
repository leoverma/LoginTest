# """
# groq_llm.py
# A thin wrapper to call Groq chat completions.
# - Uses the official groq client if installed; otherwise falls back to the REST API.
# - Exposes chat(messages, temperature, max_tokens) -> str
# """

# import os
# import json
# import time
# import requests

# # Try to import official groq client
# try:
#     from groq import Groq
#     _HAS_GROQ_PKG = True
# except Exception:
#     _HAS_GROQ_PKG = False

# # Config
# GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3.1-70b")  # default model, change as needed
# GROQ_API_HOST = os.getenv("GROQ_API_HOST", "https://api.groq.com")  # change if different

# # Initialize official client if available
# _groq_client = None
# if _HAS_GROQ_PKG:
#     try:
#         _groq_client = Groq(api_key=GROQ_API_KEY)
#     except Exception:
#         _groq_client = None

# def _http_chat(messages, temperature=0.0, max_tokens=1500):
#     """
#     Fallback HTTP call to Groq's chat endpoint.
#     The exact endpoint & payload may vary across providers — adjust if Groq's API differs.
#     """
#     url = GROQ_API_HOST.rstrip("/") + "/v1/chat/completions"
#     headers = {
#         "Authorization": f"Bearer {GROQ_API_KEY}",
#         "Content-Type": "application/json"
#     }
#     payload = {
#         "model": GROQ_MODEL,
#         "messages": messages,
#         "temperature": temperature,
#         "max_tokens": max_tokens
#     }

#     resp = requests.post(url, json=payload, headers=headers, timeout=120)
#     if resp.status_code >= 400:
#         raise RuntimeError(f"GROQ HTTP error {resp.status_code}: {resp.text}")

#     data = resp.json()
#     # Standardize response: try multiple known shapes
#     # Common shape: { choices: [ { message: { content: "..." } } ] }
#     if isinstance(data, dict):
#         choices = data.get("choices")
#         if choices and isinstance(choices, list) and len(choices) > 0:
#             first = choices[0]
#             if isinstance(first, dict):
#                 message = first.get("message") or first.get("text") or first.get("content")
#                 if isinstance(message, dict):
#                     return message.get("content") or json.dumps(message)
#                 if isinstance(message, str):
#                     return message
#         # fallback: 'message' top-level
#         if "message" in data and isinstance(data["message"], dict):
#             return data["message"].get("content") or json.dumps(data["message"])
#         if "response" in data and isinstance(data["response"], str):
#             return data["response"]
#     # fallback to raw text
#     return resp.text

# def _pkg_chat(messages, temperature=0.0, max_tokens=1500):
#     """
#     Use installed Groq package if available. Different client versions may have different call signatures.
#     Support common patterns - adjust to your installed client version if necessary.
#     """
#     if not _groq_client:
#         raise RuntimeError("Groq package initialized failed or not available")

#     # Example call pattern (adjust if your groq client differs)
#     # resp = _groq_client.chat.create(model=GROQ_MODEL, messages=messages, temperature=temperature, max_tokens=max_tokens)
#     # We will try a few possible call styles to be robust
#     try:
#         if hasattr(_groq_client, "chat") and hasattr(_groq_client.chat, "completions"):
#             resp = _groq_client.chat.completions.create(
#                 model=GROQ_MODEL,
#                 messages=messages,
#                 temperature=temperature,
#                 max_tokens=max_tokens
#             )
#             # Normalize
#             return resp.choices[0].message["content"]
#         # alternate style
#         if hasattr(_groq_client, "completions"):
#             resp = _groq_client.completions.create(
#                 model=GROQ_MODEL,
#                 messages=messages,
#                 temperature=temperature,
#                 max_tokens=max_tokens
#             )
#             return resp.choices[0].message["content"]
#     except Exception as e:
#         raise RuntimeError(f"Groq package call failed: {e}")

#     raise RuntimeError("Unsupported Groq client interface")

# def chat(messages, temperature=0.0, max_tokens=1500, retries=2):
#     """
#     messages: list of {"role": "...", "content": "..."}
#     returns: assistant content (str)
#     """
#     last_err = None
#     for attempt in range(retries + 1):
#         try:
#             if _HAS_GROQ_PKG and _groq_client:
#                 return _pkg_chat(messages, temperature=temperature, max_tokens=max_tokens)
#             else:
#                 return _http_chat(messages, temperature=temperature, max_tokens=max_tokens)
#         except Exception as e:
#             last_err = e
#             wait = 1.5 * (2 ** attempt)
#             print(f"[groq_llm] attempt {attempt+1} failed: {e}; retrying in {wait:.1f}s")
#             time.sleep(wait)
#     raise RuntimeError(f"groq chat failed after retries: {last_err}")


import time
from groq import Groq

groq_model="llama-3.1-70b-versatile"

class GroqLLM:
    def __init__(self, api_key, model=groq_model, max_retries=3):
        self.client = Groq(api_key=api_key)
        self.model = model
        self.max_retries = max_retries

    def chat(self, messages):
        last_err = None

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=0.2,
                    max_tokens=4096,
                    messages=messages
                )

                return response.choices[0].message.content

            except Exception as e:
                last_err = e
                print(f"[Groq Error] Attempt {attempt+1}/{self.max_retries}: {e}")
                time.sleep(1.5)

        raise RuntimeError(f"groq chat failed after retries: {last_err}")
