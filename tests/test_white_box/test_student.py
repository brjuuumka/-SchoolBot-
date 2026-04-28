import unittest
from unittest.mock import Mock
from bot.student import StudentHandler


class TestStudentWhiteBox(unittest.TestCase):
    """Структурные тесты ученика (белый ящик) - Разработчик"""

    def setUp(self):
        self.mock_db = Mock()
        self.student = StudentHandler(self.mock_db)

    def test_get_grades_empty(self):
        self.mock_db.get_grades_by_student.return_value = []
        grades = self.mock_db.get_grades_by_student(1)
        self.assertEqual(len(grades), 0)

    def test_get_grades_multiple(self):
        self.mock_db.get_grades_by_student.return_value = [
            {'subject': 'Math', 'grade': 5, 'date': '2024-01-01'},
            {'subject': 'Math', 'grade': 4, 'date': '2024-01-02'}
        ]
        grades = self.mock_db.get_grades_by_student(1)
        self.assertEqual(len(grades), 2)

    def test_calculate_average_grade(self):
        grades = [5, 4, 5, 3]
        avg = sum(grades) / len(grades)
        self.assertEqual(avg, 4.25)

    def test_filter_schedule_by_day(self):
        schedule = [
            {'day_of_week': 1, 'subject': 'Math'},
            {'day_of_week': 1, 'subject': 'Russian'},
            {'day_of_week': 2, 'subject': 'Physics'}
        ]
        monday = [s for s in schedule if s['day_of_week'] == 1]
        self.assertEqual(len(monday), 2)


if __name__ == '__main__':
    unittest.main()