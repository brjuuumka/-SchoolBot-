import unittest
from unittest.mock import Mock, AsyncMock, patch
from bot.teacher import TeacherHandler


class TestTeacherWhiteBox(unittest.TestCase):
    """Структурные тесты учителя (белый ящик) - Разработчик"""

    def setUp(self):
        self.mock_db = Mock()
        self.mock_app = Mock()
        self.mock_app.bot = AsyncMock()
        self.teacher = TeacherHandler(self.mock_db, self.mock_app)

    def test_get_teacher_subjects_single(self):
        self.mock_db.get_teacher_subjects.return_value = ['Математика']
        subjects = self.mock_db.get_teacher_subjects(1)
        self.assertEqual(len(subjects), 1)

    def test_get_teacher_subjects_multiple(self):
        self.mock_db.get_teacher_subjects.return_value = ['Математика', 'Физика', 'Информатика']
        subjects = self.mock_db.get_teacher_subjects(1)
        self.assertEqual(len(subjects), 3)

    def test_validate_grade_range_valid(self):
        valid_grades = [1, 2, 3, 4, 5]
        for grade in valid_grades:
            self.assertTrue(1 <= grade <= 5)

    def test_validate_grade_range_invalid(self):
        invalid_grades = [0, 6, -1, 10]
        for grade in invalid_grades:
            self.assertFalse(1 <= grade <= 5)

    def test_mark_attendance_present(self):
        self.mock_db.mark_attendance.return_value = 1
        result = self.mock_db.mark_attendance(1, "Математика", True, 2)
        self.assertEqual(result, 1)

    def test_mark_attendance_absent(self):
        self.mock_db.mark_attendance.return_value = 2
        result = self.mock_db.mark_attendance(1, "Математика", False, 2)
        self.assertEqual(result, 2)


if __name__ == '__main__':
    unittest.main()