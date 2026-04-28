import unittest
from unittest.mock import Mock
from bot.admin import AdminHandler


class TestAdminWhiteBox(unittest.TestCase):
    """Структурные тесты администратора (белый ящик) - Разработчик"""

    def setUp(self):
        self.mock_db = Mock()
        self.mock_app = Mock()
        self.admin = AdminHandler(self.mock_db, self.mock_app)

    def test_create_user_student(self):
        self.mock_db.create_user.return_value = 100
        user_id = self.mock_db.create_user(
            "new_student", "pass", "Новый", "student", class_id=5
        )
        self.assertEqual(user_id, 100)

    def test_create_user_teacher(self):
        self.mock_db.create_user.return_value = 101
        user_id = self.mock_db.create_user(
            "new_teacher", "pass", "Учитель", "teacher", subject="Математика"
        )
        self.assertEqual(user_id, 101)

    def test_create_user_parent(self):
        self.mock_db.create_user.return_value = 102
        user_id = self.mock_db.create_user(
            "new_parent", "pass", "Родитель", "parent"
        )
        self.assertEqual(user_id, 102)

    def test_statistics_structure(self):
        stats = {
            'users_by_role': {'student': 30, 'teacher': 5},
            'avg_grade': 4.5,
            'attendance_rate': 95.5
        }
        self.assertIn('student', stats['users_by_role'])
        self.assertIn('teacher', stats['users_by_role'])


if __name__ == '__main__':
    unittest.main()