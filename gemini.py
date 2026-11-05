import os
import requests
import logging

logger = logging.getLogger(__name__)

class GeminiAPI:
    def __init__(self):
        raw_key = os.environ.get("GEMINI_API_KEY", "")
        # Очищаем ключ от любых паразитных символов и пробелов
        self.api_key = raw_key.strip().replace("\n", "").replace("\r", "").replace(" ", "")
        # Стабильная и быстрая модель Gemini 1.5 Flash
        self.url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

    def generate_response(self, prompt: str) -> str:
        if not self.api_key:
            return "Ошибка: GEMINI_API_KEY не задан в настройках Render."

        # Для токенов типа AQ передаем оба варианта заголовков
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "x-goog-api-key": self.api_key
        }

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }

        try:
            response = requests.post(self.url, headers=headers, json=payload, timeout=30)
            data = response.json()

            if response.status_code != 200:
                logger.error(f"Google API Error ({response.status_code}): {data}")
                error_msg = data.get("error", {}).get("message", "Неизвестная ошибка")
                return f"Ошибка Gemini API ({response.status_code}): {error_msg}"

            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "Пустой ответ от нейросети.")

            return "Не удалось извлечь ответ нейросети."

        except Exception as e:
            logger.error(f"Исключение при обращении к Gemini: {e}")
            return f"Сетевая ошибка при обращении к AI: {e}"