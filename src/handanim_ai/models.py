import json
import requests


class OpenRouterModel:

    base_url: str = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, model_name: str, api_key: str):
        self.model_name = model_name
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "handanim",
            "X-Title": "handanim",
        }

    def invoke(self, messages: list[str], system_message: str = None) -> str:
        message_list = []
        if system_message:
            message_list.append({"role": "system", "content": system_message})

        current_role = "user"  # starts with user message
        for message in messages:
            message_list.append({"role": current_role, "content": message})
            current_role = (
                "assistant" if current_role == "user" else "user"
            )  # switch roles

        payload = {"model": self.model_name, "messages": message_list}
        response = requests.post(
            self.base_url,
            headers=self.headers,
            json=json.dumps(payload),
        )
        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code} - {response.text}")
        response_data = response.json()
        if "choices" not in response_data or len(response_data["choices"]) == 0:
            raise Exception("No choices found in the response.")
        return response_data["choices"][0]["message"]["content"]
