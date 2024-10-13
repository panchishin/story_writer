import os
import time
from groq import Groq


class Groq:
    def __init__(self, model="llama3-8b-8192"):
        self.model=model
        self.client = Groq( api_key=os.environ.get("GROQ_API_KEY") )

    def process(self, text, temperature=0.0):
        time.sleep(10) # sleep a bit to avoid server limit rate
        chat_completion = self.client.chat.completions.create(
            messages=[{"role": "user", "content": text}],
            model=self.model,
            temperature=temperature
        )
        result = chat_completion.choices[0].message.content
        return result
