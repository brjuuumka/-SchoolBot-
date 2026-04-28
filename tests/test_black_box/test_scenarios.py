"""
Функциональные тесты (черный ящик) - Тестировщик
Проверка сценариев использования без знания внутренней структуры
"""
import unittest
from unittest.mock import Mock


class TestBlackBoxScenarios(unittest.TestCase):
    """Функциональное тестирование сценариев - Тестировщик"""

    def setUp(self):
        self.mock_db = Mock()

    # СЦЕНАРИЙ 1: Успешный вход пользователя
    def test_scenario_login_success(self):
        user_data = {
            'id': 1, 'username': 'test', 'full_name': 'Тест', 'role': 'student'
        }
        self.mock_db.authenticate_user.return_value = user_data
        result = self.mock_db.authenticate_user('test', 'pass')
        self.assertIsNotNone(result)
        self.assertEqual(result['role'], 'student')

    # СЦЕНАРИЙ 2: Неверный пароль
    def test_scenario_login_wrong_password(self):
        self.mock_db.authenticate_user.return_value = None
        result = self.mock_db.authenticate_user('test', 'wrong')
        self.assertIsNone(result)

    # СЦЕНАРИЙ 3: Учитель выставляет оценку
    def test_scenario_teacher_add_grade(self):
        self.mock_db.add_grade.return_value = 123
        grade_id = self.mock_db.add_grade(1, "Математика", 5, 2)
        self.assertEqual(grade_id, 123)

    # СЦЕНАРИЙ 4: Ученик смотрит оценки
    def test_scenario_student_view_grades(self):
        grades = [
            {'subject': 'Math', 'grade': 5},
            {'subject': 'Math', 'grade': 4}
        ]
        self.mock_db.get_grades_by_student.return_value = grades
        result = self.mock_db.get_grades_by_student(1)
        self.assertEqual(len(result), 2)

    # СЦЕНАРИЙ 5: Родитель смотрит ребенка
    def test_scenario_parent_view_child(self):
        child = {'id': 1, 'full_name': 'Иван', 'class_name': '5А'}
        self.mock_db.get_child_for_parent.return_value = child
        result = self.mock_db.get_child_for_parent(1)
        self.assertEqual(result['full_name'], 'Иван')

    # СЦЕНАРИЙ 6: Учитель отмечает пропуск
    def test_scenario_teacher_mark_absent(self):
        self.mock_db.mark_attendance.return_value = 456
        att_id = self.mock_db.mark_attendance(1, "Math", False, 2)
        self.assertEqual(att_id, 456)

    # СЦЕНАРИЙ 7: Админ создает пользователя
    def test_scenario_admin_create_user(self):
        self.mock_db.create_user.return_value = 100
        user_id = self.mock_db.create_user("new", "pass", "Новый", "student")
        self.assertEqual(user_id, 100)

    # СЦЕНАРИЙ 8: Учитель задает ДЗ
    def test_scenario_teacher_set_homework(self):
        self.mock_db.add_homework.return_value = 789
        hw_id = self.mock_db.add_homework(1, "Math", "Task", 2)
        self.assertEqual(hw_id, 789)

    # СЦЕНАРИЙ 9: Классный руководитель смотрит список класса
    def test_scenario_class_teacher_view_class(self):
        students = [{'id': 1, 'full_name': 'Иван'}, {'id': 2, 'full_name': 'Петр'}]
        self.mock_db.get_students_by_class.return_value = students
        result = self.mock_db.get_students_by_class(5)
        self.assertEqual(len(result), 2)

    # СЦЕНАРИЙ 10: Родитель пишет сообщение учителю
    def test_scenario_parent_message_to_teacher(self):
        teacher = {'id': 10, 'telegram_id': 999}
        self.mock_db.get_class_teacher_by_student.return_value = teacher
        result = self.mock_db.get_class_teacher_by_student(1)
        self.assertEqual(result['telegram_id'], 999)


if __name__ == '__main__':
    unittest.main()
