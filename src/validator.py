"""
Модуль валидации данных.
Проверяет ответ от LLM на соответствие формату CSV перед сохранением.
"""

import pandas as pd
from io import StringIO
import os

def save_csv_safely(raw_data: str, output_path: str) -> bool:
    """
    Пытается распарсить строку от LLM как CSV таблицу.
    Если структура сломана (кривые разделители), pandas выдаст ошибку, 
    и мы безопасно вернем False, не сохраняя битый файл.
    """
    # Проверка на пустой ответ или триггер-слово "нет таблицы"
    if raw_data == "NO_TABLE" or not raw_data:
        return False
    
    try:
        # Оборачиваем строку в StringIO, чтобы pandas воспринимал её как файл
        df = pd.read_csv(StringIO(raw_data), sep=';')
        
        # Если модель вернула заголовки, но без данных, отбрасываем
        if df.empty:
            return False
            
        # Сохраняем чистый, провалидированный CSV на диск
        df.to_csv(output_path, index=False, sep=';')
        return True
    except Exception:
        # Перехватываем pd.errors.ParserError и любые другие сбои парсинга
        return False