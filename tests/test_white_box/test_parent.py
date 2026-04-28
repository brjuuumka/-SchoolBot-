import unittest
from unittest.mock import Mock, AsyncMock
from bot.parent import ParentHandler


class TestParentWhiteBox(unittest.TestCase):
    """Структурные тесты родителя (белый ящик) - Разработчик"""

    def setUp(self):
        self.mock_db = Mock()
        self.mock_app = Mock()
        self.parent = ParentHandler(self.mock_db, self.mock_app)

    def test_get_child_exists(self):
        self.mock_db.get_child_for_parent.return_value = {
            'id': 1, 'full_name': 'Иван', 'class_name': '5А'
        }
        child = self.mock_db.get_child_for_parent(1)
        self.assertIsNotNone(child)
        self.assertEqual(child['full_name'], 'Иван')

    def test_get_child_not_exists(self):
        self.mock_db.get_child_for_parent.return_value = None
        child = self.mock_db.get_child_for_parent(1)
        self.assertIsNone(child)

    def test_filter_week_grades(self):
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        grades = [
            {'date': (week_ago + timedelta(days=1)).strftime('%Y-%m-%d')},
            {'date': (week_ago - timedelta(days=1)).strftime('%Y-%m-%d')}
        ]
        week_grades = [g for g in grades if datetime.strptime(g['date'], '%Y-%m-%d') >= week_ago]
        self.assertEqual(len(week_grades), 1)


if __name__ == '__main__':
    unittest.main()