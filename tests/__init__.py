
"""
SchoolBot - Модуль тестирования
================================

Структура тестов:
- test_white_box/   - Структурное тестирование (разработчик)
- test_black_box/   - Функциональное тестирование (тестировщик)

Запуск тестов:
    pytest tests/ -v                           # Все тесты
    pytest tests/test_white_box/ -v            # Только структурные
    pytest tests/test_black_box/ -v            # Только функциональные
    pytest tests/test_white_box/test_database.py -v  # Конкретный файл

Покрытие кода:
    pytest tests/ --cov=bot --cov-report=html

Авторы:
    Разработчик: Структурные тесты (белый ящик)
    Тестировщик: Функциональные тесты (черный ящик)
"""

__version__ = '1.0.0'
__all__ = ['conftest']

# Импорт общих фикстур для всех тестов
from tests.conftest import *
