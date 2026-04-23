"""
Модуль для работы с API OpenAI.
Инкапсулирует логику отправки картинок в Vision-модель и обработку ошибок сети.
"""

import time
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential
from src.config import SYSTEM_PROMPT, MODEL_NAME

class VLMClient:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    # Декоратор @retry (библиотека tenacity) - защита от падений API.
    # Если OpenAI ответит ошибкой (например, 429 Too Many Requests или 500), 
    # скрипт не упадет, а подождет и попробует снова.
    # Максимум 5 попыток, пауза увеличивается экспоненциально (от 5 до 20 секунд).
    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=5, max=20))
    def request_csv(self, base64_image: str) -> str:
        """
        Отправляет base64-изображение в OpenAI и возвращает строку с CSV.
        """
        # Искусственная пауза перед каждым запросом.
        # Необходима для соблюдения жестких лимитов бесплатных/базовых ключей API.
        time.sleep(2) 
        
        response = self.client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract table to CSV."},
                        # detail: "high" указывает модели смотреть на картинку в высоком разрешении,
                        # это критически важно для чтения мелкого текста в финансовых отчетах.
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}", "detail": "high"}}
                    ]
                }
            ],
            # temperature=0.0 отключает креативность модели. 
            # Нам нужны точные данные, а не галлюцинации.
            temperature=0.0
        )
        
        # Возвращаем очищенный от пробелов и переносов текст ответа
        return response.choices[0].message.content.strip()