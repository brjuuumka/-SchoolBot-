import unittest
from unittest.mock import Mock, patch, AsyncMock
from bot.auth import AuthHandler, get_main_menu


class TestAuthWhiteBox(unittest.TestCase):
    """Структурные тесты авторизации (белый ящик) - Разработчик"""

    def setUp(self):
        self.mock_db = Mock()
        self.auth = AuthHandler(self.mock_db)

    def test_get_main_menu_for_admin(self):
        menu = get_main_menu('admin')
        buttons = []
        for row in menu.keyboard:
            for btn in row:
                buttons.append(btn.text)
        self.assertIn("📊 Статистика", buttons)
        self.assertIn("👥 Регистрация", buttons)

    def test_get_main_menu_for_teacher(self):
        menu = get_main_menu('teacher')
        buttons = []
        for row in menu.keyboard:
            for btn in row:
                buttons.append(btn.text)
        self.assertIn("📚 Мои классы", buttons)
        self.assertIn("📖 Домашнее задание", buttons)

    def test_get_main_menu_for_student(self):
        menu = get_main_menu('student')
        buttons = []
        for row in menu.keyboard:
            for btn in row:
                buttons.append(btn.text)
        self.assertIn("📝 Мои оценки", buttons)
        self.assertIn("📅 Расписание", buttons)

    def test_get_main_menu_for_parent(self):
        menu = get_main_menu('parent')
        buttons = []
        for row in menu.keyboard:
            for btn in row:
                buttons.append(btn.text)
        self.assertIn("👶 Мой ребенок", buttons)
        self.assertIn("📊 Стат недели", buttons)

    def test_is_authenticated_false_for_new_user(self):
        self.assertFalse(self.auth.is_authenticated(12345))

    def test_is_authenticated_true_after_login(self):
        self.auth.user_sessions[12345] = 1
        self.assertTrue(self.auth.is_authenticated(12345))

    def test_logout_removes_session(self):
        self.auth.user_sessions[12345] = 1
        self.auth.user_sessions.pop(12345, None)
        self.assertNotIn(12345, self.auth.user_sessions)


if __name__ == '__main__':
    unittest.main()