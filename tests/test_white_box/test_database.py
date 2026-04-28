import unittest
import tempfile
import os
from bot.datebase import Database


class TestDatabaseWhiteBox(unittest.TestCase):
    """Структурные тесты базы данных (белый ящик) - Разработчик"""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.db_path = self.temp_db.name
        self.temp_db.close()
        self.db = Database(self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    # === ТЕСТЫ СОЗДАНИЯ ПОЛЬЗОВАТЕЛЕЙ ===
    def test_create_user_success(self):
        user_id = self.db.create_user("test_user", "pass123", "Тест", "student")
        self.assertIsNotNone(user_id)
        self.assertIsInstance(user_id, int)

    def test_create_user_duplicate_username(self):
        self.db.create_user("test_user", "pass123", "Тест", "student")
        user_id = self.db.create_user("test_user", "pass456", "Другой", "student")
        self.assertIsNone(user_id)

    def test_create_user_with_class(self):
        user_id = self.db.create_user("test_student", "pass", "Ученик", "student", class_id=1)
        user = self.db.get_user_by_id(user_id)
        self.assertEqual(user['class_id'], 1)

    def test_create_user_with_subject(self):
        user_id = self.db.create_user("test_teacher", "pass", "Учитель", "teacher", subject="Математика,Физика")
        subjects = self.db.get_teacher_subjects(user_id)
        self.assertEqual(len(subjects), 2)
        self.assertIn("Математика", subjects)

    # === ТЕСТЫ АУТЕНТИФИКАЦИИ ===
    def test_authenticate_valid_user(self):
        self.db.create_user("valid_user", "correct_pass", "Пользователь", "student")
        user = self.db.authenticate_user("valid_user", "correct_pass")
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], "valid_user")

    def test_authenticate_invalid_password(self):
        self.db.create_user("valid_user", "correct_pass", "Пользователь", "student")
        user = self.db.authenticate_user("valid_user", "wrong_pass")
        self.assertIsNone(user)

    def test_authenticate_nonexistent_user(self):
        user = self.db.authenticate_user("ghost_user", "any_pass")
        self.assertIsNone(user)

    # === ТЕСТЫ ОЦЕНОК ===
    def test_add_grade_min(self):
        grade_id = self.db.add_grade(1, "Математика", 1, 2)
        self.assertIsNotNone(grade_id)

    def test_add_grade_max(self):
        grade_id = self.db.add_grade(1, "Математика", 5, 2)
        self.assertIsNotNone(grade_id)

    def test_get_grades_by_student(self):
        self.db.add_grade(1, "Математика", 5, 2)
        self.db.add_grade(1, "Русский", 4, 2)
        grades = self.db.get_grades_by_student(1)
        self.assertEqual(len(grades), 2)

    def test_average_grade_calculation(self):
        self.db.add_grade(1, "Математика", 5, 2)
        self.db.add_grade(1, "Математика", 3, 2)
        avg = self.db.get_average_grade_by_student(1, "Математика")
        self.assertEqual(avg, 4.0)

    # === ТЕСТЫ ПОСЕЩАЕМОСТИ ===
    def test_mark_attendance_present(self):
        attendance_id = self.db.mark_attendance(1, "Математика", True, 2)
        self.assertIsNotNone(attendance_id)
        attendance = self.db.get_attendance_by_student(1)
        self.assertTrue(attendance[0]['is_present'])

    def test_mark_attendance_absent(self):
        attendance_id = self.db.mark_attendance(1, "Математика", False, 2)
        self.assertIsNotNone(attendance_id)
        attendance = self.db.get_attendance_by_student(1)
        self.assertFalse(attendance[0]['is_present'])

    # === ТЕСТЫ ДОМАШНИХ ЗАДАНИЙ ===
    def test_add_homework(self):
        hw_id = self.db.add_homework(1, "Математика", "Решить задачу", 2)
        self.assertIsNotNone(hw_id)

    def test_get_homeworks_by_class(self):
        self.db.add_homework(1, "Математика", "Задание 1", 2)
        self.db.add_homework(1, "Русский", "Задание 2", 2)
        homeworks = self.db.get_homeworks_by_class(1)
        self.assertGreaterEqual(len(homeworks), 2)

    # === ТЕСТЫ ЗАМЕЧАНИЙ ===
    def test_add_comment(self):
        comment_id = self.db.add_comment(1, 2, "Поведение", "Разговаривал")
        self.assertIsNotNone(comment_id)

    def test_get_comments_by_student(self):
        self.db.add_comment(1, 2, "Поведение", "Замечание 1")
        self.db.add_comment(1, 2, "Дисциплина", "Замечание 2")
        comments = self.db.get_comments_by_student(1)
        self.assertEqual(len(comments), 2)

    # === ТЕСТЫ СВЯЗИ РОДИТЕЛЬ-РЕБЕНОК ===
    def test_link_parent_to_student(self):
        parent_id = self.db.create_user("parent", "pass", "Родитель", "parent")
        child_id = self.db.create_user("child", "pass", "Ребенок", "student")
        result = self.db.link_parent_to_student(parent_id, child_id)
        self.assertTrue(result)

    def test_get_child_for_parent(self):
        parent_id = self.db.create_user("parent", "pass", "Родитель", "parent")
        child_id = self.db.create_user("child", "pass", "Ребенок", "student")
        self.db.link_parent_to_student(parent_id, child_id)
        child = self.db.get_child_for_parent(parent_id)
        self.assertEqual(child['id'], child_id)

    # === ТЕСТЫ СТАТИСТИКИ ===
    def test_get_school_statistics_structure(self):
        stats = self.db.get_school_statistics()
        self.assertIn('users_by_role', stats)
        self.assertIn('avg_grade', stats)
        self.assertIn('attendance_rate', stats)

    def test_statistics_values_are_valid(self):
        stats = self.db.get_school_statistics()
        self.assertIsInstance(stats['avg_grade'], (int, float))
        self.assertGreaterEqual(stats['attendance_rate'], 0)
        self.assertLessEqual(stats['attendance_rate'], 100)


if __name__ == '__main__':
    unittest.main()
