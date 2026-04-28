import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock
from bot.datebase import Database
from bot.auth import AuthHandler
from bot.admin import AdminHandler
from bot.teacher import TeacherHandler
from bot.student import StudentHandler
from bot.parent import ParentHandler

@pytest.fixture
def temp_db():
    """Создание временной БД для тестов"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp:
        db_path = tmp.name
    db = Database(db_path)
    yield db
    os.unlink(db_path)

@pytest.fixture
def mock_db():
    """Мок базы данных"""
    return Mock(spec=Database)

@pytest.fixture
def mock_app():
    """Мок приложения"""
    app = Mock()
    app.bot = AsyncMock()
    return app

@pytest.fixture
def auth_handler(mock_db):
    """AuthHandler с мок БД"""
    return AuthHandler(mock_db)

@pytest.fixture
def admin_handler(mock_db, mock_app):
    """AdminHandler с моками"""
    return AdminHandler(mock_db, mock_app)

@pytest.fixture
def teacher_handler(mock_db, mock_app):
    """TeacherHandler с моками"""
    return TeacherHandler(mock_db, mock_app)

@pytest.fixture
def student_handler(mock_db):
    """StudentHandler с мок БД"""
    return StudentHandler(mock_db)

@pytest.fixture
def parent_handler(mock_db, mock_app):
    """ParentHandler с моками"""
    return ParentHandler(mock_db, mock_app)

@pytest.fixture
def sample_user():
    """Пример пользователя для тестов"""
    return {
        'id': 1,
        'username': 'test_user',
        'full_name': 'Тестовый Пользователь',
        'role': 'student',
        'class_id': 5,
        'telegram_id': 123456789
    }

@pytest.fixture
def sample_grade():
    """Пример оценки для тестов"""
    return {
        'id': 1,
        'student_id': 1,
        'subject': 'Математика',
        'grade': 5,
        'teacher_id': 2,
        'date': '2024-01-15'
    }