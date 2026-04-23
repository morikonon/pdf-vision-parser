"""
Модуль рендеринга PDF.
Отвечает исключительно за конвертацию страниц PDF-документа в растровые изображения.
"""

import fitz  # PyMuPDF
import base64

def render_page_to_base64(pdf_path: str, page_num: int, dpi: int) -> str:
    """
    Превращает конкретную страницу PDF в строку формата base64 (PNG).
    Мы используем base64, чтобы отправлять картинку в OpenAI API напрямую из памяти,
    минуя сохранение промежуточных файлов на жесткий диск.
    """
    with fitz.open(pdf_path) as doc:
        page = doc.load_page(page_num)
        
        # Вычисляем коэффициент масштабирования (DPI 72 - это стандартный масштаб 100%)
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        
        # get_pixmap рендерит страницу в изображение с учетом нашей матрицы
        pix = page.get_pixmap(matrix=mat)
        
        # Кодируем байты изображения в base64 и переводим в строку
        return base64.b64encode(pix.tobytes("png")).decode("utf-8")