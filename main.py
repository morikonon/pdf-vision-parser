""""
Главный модуль (Оркестратор).
Связывает все компоненты системы воедино: чтение PDF -> рендер -> запрос к LLM -> валидация -> сохранение.
Поддерживает многопоточную обработку для ускорения пайплайна.
"""

import os
import glob 
import pandas as pd
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

def merge_to_excel(output_dir: str, final_name: str = "Financial_Report_Parsed.xlsx"):
    """Собирает все сгенерированные CSV в один красивый Excel-файл с вкладками."""
    csv_files = glob.glob(os.path.join(output_dir, "page_*.csv"))
    if not csv_files:
        logger.warning("Нет файлов для склейки в Excel.")
        return

    # Сортируем файлы по номеру страницы, чтобы вкладки шли по порядку
    csv_files.sort(key=lambda x: int(os.path.basename(x).split('_')[1].split('.')[0]))

    final_file_path = os.path.join(output_dir, final_name)
    
    # Открываем "писатель" Excel
    with pd.ExcelWriter(final_file_path, engine='openpyxl') as writer:
        for file in csv_files:
            try:
                df = pd.read_csv(file, sep=';')
                # Название вкладки будет "Page 10", "Page 12" и т.д.
                sheet_name = os.path.basename(file).replace('.csv', '').replace('_', ' ').title()
                
                # Записываем датафрейм на отдельный лист
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            except Exception as e:
                logger.error(f"Ошибка при добавлении {file} в Excel: {e}")

    logger.info(f"УСПЕХ: Все таблицы собраны в один Excel-файл -> {final_file_path}")


def merge_csv_files(output_dir: str, final_name: str = "merged_result.csv"): 
    """Собирает все сгенерированные CSV в один итоговый файл."""
    csv_files = glob.glob(os.path.join(output_dir, "page_*.csv"))
    if not csv_files:
        logger.warning("Нет файлов для склейки.")
        return

    df_list = []
    for file in csv_files:
        try:
            df = pd.read_csv(file, sep=';')
            # Добавляем колумн с указанием страницы
            df["source_page"] = os.path.basename(file)
            df_list.append(df)
        except Exception as e:
            logger.error(f"Ошибка чтения {file} при склейке: {e}")
    
    if df_list:
        final_df = pd.concat(df_list, ignore_index=True)
        final_df_path = os.path.join(output_dir, final_name)
        final_df.to_csv(final_df_path, index=False, sep=';')
        logger.info(f"Успех: {len(csv_files)} таблиц склеены в один файл -> {final_name}")


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

    # Склеиваем все в конце
    merge_csv_files(output_dir)
    merge_to_excel(output_dir)

if __name__ == "__main__":
    # Запуск пайплайна (название файла должно лежать в папке input/)
    main("mycar.pdf")