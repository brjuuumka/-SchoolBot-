import sqlite3
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

class Database:
    def __init__(self, db_path: str = "schoolbot.db"):
        self.db_path = db_path
        self.init_tables()
    
    @contextmanager
    def get_connection(self):
        """Контекстный менеджер для соединения с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Чтобы можно было обращаться по именам колонок
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def init_tables(self):
        """Создаёт все таблицы, если их нет"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('student', 'parent', 'teacher', 'class_teacher', 'admin')),
                    class_id INTEGER,
                    subject TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица классов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    class_teacher_id INTEGER,
                    FOREIGN KEY (class_teacher_id) REFERENCES users(id)
                )
            ''')
            
            # Таблица связей родитель-ребёнок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS student_parents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    parent_id INTEGER NOT NULL,
                    FOREIGN KEY (student_id) REFERENCES users(id),
                    FOREIGN KEY (parent_id) REFERENCES users(id),
                    UNIQUE(student_id, parent_id)
                )
            ''')
            
            # Таблица оценок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS grades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    grade INTEGER NOT NULL CHECK(grade BETWEEN 1 AND 5),
                    teacher_id INTEGER NOT NULL,
                    date DATE DEFAULT CURRENT_DATE,
                    comment TEXT,
                    FOREIGN KEY (student_id) REFERENCES users(id),
                    FOREIGN KEY (teacher_id) REFERENCES users(id)
                )
            ''')
            
            # Таблица посещаемости
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    date DATE DEFAULT CURRENT_DATE,
                    is_present BOOLEAN DEFAULT 1,
                    teacher_id INTEGER NOT NULL,
                    FOREIGN KEY (student_id) REFERENCES users(id),
                    FOREIGN KEY (teacher_id) REFERENCES users(id)
                )
            ''')
            
            # Таблица домашних заданий
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS homeworks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    text TEXT NOT NULL,
                    assigned_date DATE DEFAULT CURRENT_DATE,
                    deadline DATE,
                    teacher_id INTEGER NOT NULL,
                    FOREIGN KEY (class_id) REFERENCES classes(id),
                    FOREIGN KEY (teacher_id) REFERENCES users(id)
                )
            ''')
            
            # Таблица замечаний
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    teacher_id INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    text TEXT NOT NULL,
                    date DATE DEFAULT CURRENT_DATE,
                    FOREIGN KEY (student_id) REFERENCES users(id),
                    FOREIGN KEY (teacher_id) REFERENCES users(id)
                )
            ''')
            
            # Таблица уведомлений
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    is_read BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # Таблица расписания
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    class_id INTEGER NOT NULL,
                    day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 1 AND 6),
                    lesson_number INTEGER NOT NULL,
                    subject TEXT NOT NULL,
                    FOREIGN KEY (class_id) REFERENCES classes(id)
                )
            ''')
    
    # ---------- ПОЛЬЗОВАТЕЛИ ----------
    
    def create_user(self, username: str, password: str, full_name: str, role: str, 
                    class_id: int = None, subject: str = None) -> Optional[int]:
        """Создаёт нового пользователя. Возвращает ID или None"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO users (username, password_hash, full_name, role, class_id, subject)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (username, password_hash, full_name, role, class_id, subject))
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Проверяет логин/пароль. Возвращает данные пользователя или None"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, full_name, role, class_id, subject, telegram_id
                FROM users WHERE username = ? AND password_hash = ?
            ''', (username, password_hash))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_telegram_id(self, user_id: int, telegram_id: int) -> bool:
        """Привязывает Telegram ID к пользователю"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET telegram_id = ? WHERE id = ?', (telegram_id, user_id))
            return cursor.rowcount > 0
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict]:
        """Получает пользователя по Telegram ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, full_name, role, class_id, subject
                FROM users WHERE telegram_id = ?
            ''', (telegram_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, full_name, role, class_id, subject, telegram_id FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ---------- КЛАССЫ ----------
    
    def create_class(self, name: str, class_teacher_id: int = None) -> Optional[int]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('INSERT INTO classes (name, class_teacher_id) VALUES (?, ?)', (name, class_teacher_id))
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None
    
    def get_all_classes(self) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, class_teacher_id FROM classes')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_class_by_id(self, class_id: int) -> Optional[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, class_teacher_id FROM classes WHERE id = ?', (class_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ---------- УЧЕНИКИ ----------
    
    def get_students_by_class(self, class_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, full_name, username FROM users 
                WHERE role = 'student' AND class_id = ?
            ''', (class_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_child_for_parent(self, parent_id: int) -> Optional[Dict]:
        """Получает ребёнка для родителя"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT u.id, u.full_name, u.class_id, c.name as class_name
                FROM student_parents sp
                JOIN users u ON sp.student_id = u.id
                LEFT JOIN classes c ON u.class_id = c.id
                WHERE sp.parent_id = ?
            ''', (parent_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def link_parent_to_student(self, parent_id: int, student_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('INSERT INTO student_parents (student_id, parent_id) VALUES (?, ?)', (student_id, parent_id))
                return True
            except sqlite3.IntegrityError:
                return False
    
    # ---------- ОЦЕНКИ ----------
    
    def add_grade(self, student_id: int, subject: str, grade: int, teacher_id: int, comment: str = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO grades (student_id, subject, grade, teacher_id, comment)
                VALUES (?, ?, ?, ?, ?)
            ''', (student_id, subject, grade, teacher_id, comment))
            return cursor.lastrowid
    
    def get_grades_by_student(self, student_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT g.*, u.full_name as teacher_name
                FROM grades g
                JOIN users u ON g.teacher_id = u.id
                WHERE g.student_id = ?
                ORDER BY g.date DESC
            ''', (student_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_average_grade_by_student(self, student_id: int, subject: str = None) -> float:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if subject:
                cursor.execute('''
                    SELECT AVG(grade) as avg FROM grades 
                    WHERE student_id = ? AND subject = ?
                ''', (student_id, subject))
            else:
                cursor.execute('SELECT AVG(grade) as avg FROM grades WHERE student_id = ?', (student_id,))
            row = cursor.fetchone()
            return row['avg'] if row and row['avg'] else 0.0
    
    # ---------- ПОСЕЩАЕМОСТЬ ----------
    
    def mark_attendance(self, student_id: int, subject: str, is_present: bool, teacher_id: int) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO attendance (student_id, subject, is_present, teacher_id)
                VALUES (?, ?, ?, ?)
            ''', (student_id, subject, is_present, teacher_id))
            return cursor.lastrowid
    
    def get_attendance_by_student(self, student_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM attendance WHERE student_id = ? ORDER BY date DESC
            ''', (student_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ---------- ДОМАШНИЕ ЗАДАНИЯ ----------
    
    def add_homework(self, class_id: int, subject: str, text: str, teacher_id: int, deadline: str = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO homeworks (class_id, subject, text, teacher_id, deadline)
                VALUES (?, ?, ?, ?, ?)
            ''', (class_id, subject, text, teacher_id, deadline))
            return cursor.lastrowid
    
    def get_homeworks_by_class(self, class_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT h.*, u.full_name as teacher_name
                FROM homeworks h
                JOIN users u ON h.teacher_id = u.id
                WHERE h.class_id = ? AND date(h.assigned_date) >= date('now', '-7 days')
                ORDER BY h.assigned_date DESC
            ''', (class_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ---------- ЗАМЕЧАНИЯ ----------
    
    def add_comment(self, student_id: int, teacher_id: int, subject: str, text: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO comments (student_id, teacher_id, subject, text)
                VALUES (?, ?, ?, ?)
            ''', (student_id, teacher_id, subject, text))
            return cursor.lastrowid
    
    def get_comments_by_student(self, student_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT c.*, u.full_name as teacher_name
                FROM comments c
                JOIN users u ON c.teacher_id = u.id
                WHERE c.student_id = ?
                ORDER BY c.date DESC
            ''', (student_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ---------- РАСПИСАНИЕ ----------
    
    def add_schedule_entry(self, class_id: int, day_of_week: int, lesson_number: int, subject: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO schedule (class_id, day_of_week, lesson_number, subject)
                VALUES (?, ?, ?, ?)
            ''', (class_id, day_of_week, lesson_number, subject))
            return cursor.lastrowid
    
    def get_schedule_by_class(self, class_id: int, day_of_week: int = None) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if day_of_week:
                cursor.execute('''
                    SELECT * FROM schedule WHERE class_id = ? AND day_of_week = ?
                    ORDER BY lesson_number
                ''', (class_id, day_of_week))
            else:
                cursor.execute('''
                    SELECT * FROM schedule WHERE class_id = ? ORDER BY day_of_week, lesson_number
                ''', (class_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # ---------- УВЕДОМЛЕНИЯ ----------
    
    def add_notification(self, user_id: int, text: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO notifications (user_id, text) VALUES (?, ?)', (user_id, text))
            return cursor.lastrowid
    
    def get_unread_notifications(self, user_id: int) -> List[Dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM notifications WHERE user_id = ? AND is_read = 0
                ORDER BY created_at DESC
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_notification_read(self, notification_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE notifications SET is_read = 1 WHERE id = ?', (notification_id,))
            return cursor.rowcount > 0
    
    # ---------- СТАТИСТИКА ----------
    
    def get_school_statistics(self) -> Dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Количество пользователей по ролям
            cursor.execute('SELECT role, COUNT(*) as count FROM users GROUP BY role')
            users_by_role = {row['role']: row['count'] for row in cursor.fetchall()}
            
            # Средний балл по школе
            cursor.execute('SELECT AVG(grade) as avg FROM grades')
            avg_grade = cursor.fetchone()['avg'] or 0
            
            # Общая посещаемость
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN is_present = 1 THEN 1 ELSE 0 END) as present,
                    COUNT(*) as total
                FROM attendance
            ''')
            attendance_stats = cursor.fetchone()
            attendance_rate = (attendance_stats['present'] / attendance_stats['total'] * 100) if attendance_stats['total'] > 0 else 0
            
            return {
                'users_by_role': users_by_role,
                'avg_grade': round(avg_grade, 2),
                'attendance_rate': round(attendance_rate, 1)
            }
