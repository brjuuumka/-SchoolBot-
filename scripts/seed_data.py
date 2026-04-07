#Тестовые данные
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.database import Database

def seed_database():
    db = Database("schoolbot.db")
    
    print("🌱 Наполняем базу тестовыми данными...")
    
    # 1. Создаём классы
    print("📚 Создаём классы...")
    class_10a = db.create_class("10А")
    class_10b = db.create_class("10Б")
    class_9a = db.create_class("9А")
    
    # 2. Создаём администратора
    print("👑 Создаём администратора...")
    admin_id = db.create_user("admin", "admin", "Администратор", "admin")
    print(f"   ✅ Админ создан (ID: {admin_id})")
    
    # 3. Создаём учителей
    print("👩‍🏫 Создаём учителей...")
    teacher_math = db.create_user("math_teacher", "123", "Иванова Мария Петровна", "teacher", subject="Математика")
    teacher_rus = db.create_user("rus_teacher", "123", "Сидорова Елена Владимировна", "teacher", subject="Русский язык")
    teacher_phys = db.create_user("phys_teacher", "123", "Кузнецов Андрей Сергеевич", "teacher", subject="Физика")
    print(f"   ✅ Учителя созданы")
    
    # 4. Создаём учеников (10А класс)
    print("👨‍🎓 Создаём учеников 10А...")
    student1 = db.create_user("ivanov", "123", "Иванов Иван Иванович", "student", class_id=class_10a)
    student2 = db.create_user("petrov", "123", "Петров Петр Петрович", "student", class_id=class_10a)
    student3 = db.create_user("sidorov", "123", "Сидоров Алексей Дмитриевич", "student", class_id=class_10a)
    print(f"   ✅ Ученики созданы")
    
    # 5. Создаём родителей
    print("👪 Создаём родителей...")
    parent1 = db.create_user("parent_ivanov", "123", "Иванова Ольга Сергеевна", "parent")
    parent2 = db.create_user("parent_petrov", "123", "Петрова Наталья Владимировна", "parent")
    print(f"   ✅ Родители созданы")
    
    # 6. Привязываем родителей к ученикам
    print("🔗 Привязываем родителей к ученикам...")
    db.link_parent_to_student(parent1, student1)
    db.link_parent_to_student(parent2, student2)
    print(f"   ✅ Привязка выполнена")
    
    # 7. Добавляем оценки
    print("📝 Добавляем тестовые оценки...")
    db.add_grade(student1, "Математика", 5, teacher_math)
    db.add_grade(student1, "Математика", 4, teacher_math)
    db.add_grade(student1, "Русский язык", 5, teacher_rus)
    db.add_grade(student1, "Физика", 4, teacher_phys)
    
    db.add_grade(student2, "Математика", 3, teacher_math)
    db.add_grade(student2, "Русский язык", 4, teacher_rus)
    db.add_grade(student2, "Физика", 5, teacher_phys)
    print(f"   ✅ Оценки добавлены")
    
    # 8. Добавляем посещаемость
    print("📋 Добавляем посещаемость...")
    db.mark_attendance(student1, "Математика", True, teacher_math)
    db.mark_attendance(student1, "Русский язык", True, teacher_rus)
    db.mark_attendance(student2, "Математика", False, teacher_math)  # Пропуск
    print(f"   ✅ Посещаемость добавлена")
    
    # 9. Добавляем замечания
    print("💬 Добавляем замечания...")
    db.add_comment(student2, teacher_math, "Математика", "Не подготовил домашнее задание")
    print(f"   ✅ Замечания добавлены")
    
    # 10. Добавляем ДЗ
    print("📖 Добавляем домашние задания...")
    db.add_homework(class_10a, "Математика", "Решить задачи №145-150 на стр. 78", teacher_math)
    db.add_homework(class_10a, "Русский язык", "Написать сочинение на тему 'Весна'", teacher_rus)
    print(f"   ✅ ДЗ добавлены")
    
    # 11. Добавляем расписание для 10А
    print("📅 Добавляем расписание для 10А...")
    days = [
        (1, "Понедельник", ["Математика", "Русский язык", "Физика", "История", "Английский язык"]),
        (2, "Вторник", ["Литература", "Алгебра", "Химия", "Биология", "Физкультура"]),
        (3, "Среда", ["Геометрия", "Русский язык", "Информатика", "Обществознание", "Физика"]),
        (4, "Четверг", ["Алгебра", "Литература", "Английский язык", "География", "Химия"]),
        (5, "Пятница", ["Русский язык", "Математика", "Физика", "История", "ОБЖ"])
    ]
    
    for day_num, day_name, subjects in days:
        for i, subject in enumerate(subjects, 1):
            db.add_schedule_entry(class_10a, day_num, i, subject)
    print(f"   ✅ Расписание добавлено")
    
    print("\n✅ База данных успешно наполнена!")
    print("\n📋 Тестовые аккаунты:")
    print("   👑 Админ: admin / admin")
    print("   👩‍🏫 Учитель математики: math_teacher / 123")
    print("   👨‍🎓 Ученик: ivanov / 123")
    print("   👪 Родитель: parent_ivanov / 123")

if __name__ == "__main__":
    seed_database()
