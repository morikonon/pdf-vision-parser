"""
Главный модуль (Оркестратор).
Связывает все компоненты системы воедино: чтение PDF -> рендер -> запрос к LLM -> валидация -> сохранение.
Поддерживает многопоточную обработку для ускорения пайплайна.
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.config import OPENAI_API_KEY, DPI, MAX_WORKERS
from src.logger import get_logger
from src.pdf_worker import render_page_to_base64
from src.llm_client import VLMClient
from src.validator import save_csv_safely
import fitz

# Инициализируем глобальные объекты логгера и API-клиента
logger = get_logger()
client = VLMClient(OPENAI_API_KEY)

def process_page(pdf_path: str, page_num: int, output_dir: str) -> bool:
    """
    Жизненный цикл обработки одной страницы.
    Изолирована в отдельную функцию для удобной передачи в ThreadPoolExecutor.
    """
    try:
        # 1. Превращаем PDF страницу в картинку (base64)
        img_b64 = render_page_to_base64(pdf_path, page_num, DPI)
        
        # 2. Отправляем картинку в Vision-модель для извлечения таблиц
        csv_text = client.request_csv(img_b64)
        
        # 3. Валидируем ответ и сохраняем на диск
        output_file = os.path.join(output_dir, f"page_{page_num+1}.csv")
        
        if save_csv_safely(csv_text, output_file):
            logger.info(f"Page {page_num+1}: Success (Таблица извлечена и сохранена)")
            return True
        
        logger.warning(f"Page {page_num+1}: No table found (Пропуск страницы)")
        
    except Exception as e:
        logger.error(f"Page {page_num+1}: Failed with error {e}")
        
    return False

def main(pdf_name: str):
    """
    Точка входа. Читает документ и распределяет страницы по воркерам.
    """
    input_path = os.path.join("input", pdf_name)
    # Создаем папку для результатов (например, output/mycar/)
    output_dir = os.path.join("output", pdf_name.replace(".pdf", ""))
    os.makedirs(output_dir, exist_ok=True)

    # Узнаем общее количество страниц в документе
    with fitz.open(input_path) as doc:
        total = doc.page_count

    logger.info(f"Starting {pdf_name}, {total} pages...")

    # Используем пул потоков для конкурентного выполнения I/O операций (сетевых запросов).
    # Количество потоков регулируется в config.py (MAX_WORKERS).
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Отправляем все страницы в пул задач
        futures = [executor.submit(process_page, input_path, i, output_dir) for i in range(total)]
        
        # Собираем результаты по мере их завершения
        results = [f.result() for f in as_completed(futures)]

    # Считаем количество успешно сохраненных таблиц (где функция вернула True)
    logger.info(f"Done! Extracted {sum(results)} tables.")

if __name__ == "__main__":
    # Запуск пайплайна (название файла должно лежать в папке input/)
    main("mycar.pdf")