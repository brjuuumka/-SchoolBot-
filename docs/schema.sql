SchoolBot Database Schema
База данных: SQLite 3

-- 1. Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('student', 'parent', 'teacher', 'class_teacher', 'admin')),
    class_id INTEGER,
    subject TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES classes(id)
);

-- 2. Таблица классов
CREATE TABLE IF NOT EXISTS classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    class_teacher_id INTEGER,
    FOREIGN KEY (class_teacher_id) REFERENCES users(id)
);

-- 3. Связь учеников с родителями (многие ко многим)
CREATE TABLE IF NOT EXISTS student_parents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    parent_id INTEGER NOT NULL,
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (parent_id) REFERENCES users(id),
    UNIQUE(student_id, parent_id)
);

-- 4. Таблица оценок
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
);

-- 5. Таблица посещаемости
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    subject TEXT NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    is_present BOOLEAN DEFAULT 1,
    teacher_id INTEGER NOT NULL,
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (teacher_id) REFERENCES users(id)
);

-- 6. Таблица домашних заданий
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
);

-- 7. Таблица замечаний
CREATE TABLE IF NOT EXISTS comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    teacher_id INTEGER NOT NULL,
    subject TEXT NOT NULL,
    text TEXT NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    FOREIGN KEY (student_id) REFERENCES users(id),
    FOREIGN KEY (teacher_id) REFERENCES users(id)
);

-- 8. Таблица уведомлений
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_read BOOLEAN DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 9. Таблица расписания
CREATE TABLE IF NOT EXISTS schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    class_id INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL CHECK(day_of_week BETWEEN 1 AND 6),
    lesson_number INTEGER NOT NULL,
    subject TEXT NOT NULL,
    teacher_id INTEGER,
    FOREIGN KEY (class_id) REFERENCES classes(id),
    FOREIGN KEY (teacher_id) REFERENCES users(id),
    UNIQUE(class_id, day_of_week, lesson_number)
);

-- Индексы для оптимизации запросов
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_grades_student_id ON grades(student_id);
CREATE INDEX idx_grades_date ON grades(date);
CREATE INDEX idx_attendance_student_id ON attendance(student_id);
CREATE INDEX idx_homeworks_class_id ON homeworks(class_id);
CREATE INDEX idx_comments_student_id ON comments(student_id);
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_schedule_class_id ON schedule(class_id);
