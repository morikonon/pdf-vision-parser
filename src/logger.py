import logging
import colorlog

# Функция для логгирования
def get_logger(name="PDF_Extractor"):
	logger = logging.getLogger(name)
	if not logger.handlers:
		logger.setLevel(logging.INFO)
		handler = logging.StreamHandler()
		formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

		handler.setFormatter(formatter)
		logger.addHandler(handler)
	
	return logger