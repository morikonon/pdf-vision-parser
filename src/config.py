"""
Модуль конфигурации пайплайна.
Содержит все изменяемые параметры: ключи, настройки рендеринга и промпты.
Это позволяет менять поведение системы, не трогая основной код.
"""

import os
from dotenv import load_dotenv

# Подтягиваем переменные окружения из файла .env (например, OPENAI_API_KEY)
load_dotenv()

# Настройки API OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Используем gpt-5.4-nano: она в 3.5 раза дешевле mini, но отлично справляется 
# с задачей data extraction (извлечения таблиц).
MODEL_NAME = "gpt-5.4-nano"

# Параметры обработки PDF
# DPI 200 — это идеальный баланс: текст уже не пикселит (LLM его хорошо видит),
# но картинка еще не весит слишком много (экономим токены и деньги).
DPI = 200

# Количество параллельных потоков. 
# Стоит 1, чтобы не словить RateLimitError (ошибку лимитов) на базовых ключах OpenAI.
MAX_WORKERS = 1

# Системный промпт (инструкция) для VLM.
# Написан с использованием жестких правил (Rules), чтобы отсечь мусор (например, оглавления)
# и заставить модель выдавать строго структурированный CSV без воды.
SYSTEM_PROMPT = (
    "You are a strict data extraction system for a bank. "
    "Your task is to extract financial, numerical, and analytical tabular data from the image into valid CSV format using ';' as delimiter. "
    "Rule 1: DO NOT extract Tables of Contents (Оглавление/Содержание). If the image is primarily a Table of Contents, output exactly: NO_TABLE. "
    "Rule 2: DO NOT extract plain text paragraphs formatted as tables. "
    "Rule 3: NO markdown formatting. NO conversational text. "
    "Rule 4: If no relevant financial/data table is visually present, output exactly: NO_TABLE."
)