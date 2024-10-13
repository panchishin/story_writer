import json
import requests

class Ollama:
    """
    A class to interact with a local LLM service using the Ollama.ai

    Format is either None or "json"
    """

    def __init__(self, *, system_prompt, model="llama3.2:3b", tokens=128000, format=None):
        self.system_prompt = system_prompt
        self.model = model
        self.format = format
        self.tokens = tokens

    def tokens(self):
        return self.tokens

    def process(self, text, temperature=0.0):
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": self.system_prompt},
                {"role": "assistant", "content": "Understood"},
                {"role": "user", "content": text},
            ],
            "options" : {"temperature":temperature},
            "stream": False,
        }
        if self.format:
            payload["format"] = self.format

        response = requests.post("http://localhost:11434/api/chat", data=json.dumps(payload), stream=False)
        return response.json().get("message", {}).get("content","").strip()
