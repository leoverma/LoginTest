import time
import os
from groq import Groq

groq_model="llama-3.3-70b-versatile"

class GroqLLM:
    def __init__(self, api_key=None, model=groq_model, max_retries=3):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = model
        self.max_retries = max_retries

    def chat(self, messages,initial_delay=10, max_retries=5):
        delay = initial_delay
        last_err = None
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=0.2,
                    max_tokens=4096,
                    messages=messages,
                )
                return response.choices[0].message.content
            except RuntimeError as e:
                if '429' in str(e):
                    print(f'[Groq Error] Rate limit hit. Retrying after {delay}s...')
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    raise
        raise RuntimeError('groq chat failed after retries (rate limit), {last_err}')
        

        # for attempt in range(self.max_retries):
        #     try:
                

        #     except Exception as e:
        #         last_err = e
        #         print(f"[Groq Error] Attempt {attempt+1}/{self.max_retries}: {e}")
        #         time.sleep(1.5)

        # raise RuntimeError(f"groq chat failed after retries: {last_err}")
