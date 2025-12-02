import time
import os
from groq import Groq

groq_model="llama-3.3-70b-versatile"

class GroqLLM:
    def __init__(self, api_key=None, model=groq_model, max_retries=3):
        self.client = Groq(os.getenv("GROQ_API_KEY"))
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
                    messages=messages,
                )
                return response.choices[0].message.content

            except Exception as e:
                last_err = e
                print(f"[Groq Error] Attempt {attempt+1}/{self.max_retries}: {e}")
                time.sleep(1.5)

        raise RuntimeError(f"groq chat failed after retries: {last_err}")
