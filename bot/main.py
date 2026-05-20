import asyncio
import logging
import warnings
from telegram.warnings import PTBUserWarning


logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

warnings.filterwarnings("ignore", message=".*CallbackQueryHandler.*", category=PTBUserWarning)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

from bot.datebase import Database
from bot.constants import TOKEN, AUTH_LOGIN, AUTH_PASSWORD, REG_ROLE, REG_FULL_NAME, REG_USERNAME, REG_PASSWORD, REG_CLASS, REG_SUBJECT, REG_CHILD, BROADCAST_TEXT, TEACHER_ENTER_GRADE, TEACHER_ENTER_COMMENT, TEACHER_ENTER_HOMEWORK, TEACHER_BROADCAST_TEXT, PARENT_MESSAGE_TO_TEACHER
from bot.auth import AuthHandler
from bot.admin import AdminHandler
from bot.teacher import TeacherHandler
from bot.student import StudentHandler
from bot.parent import ParentHandler


class SchoolBot:
    def __init__(self):
        self.db = Database("schoolbot.db")
        self.app = None
        self.auth = AuthHandler(self.db)
        self.admin = None
        self.teacher = None
        self.student = StudentHandler(self.db)
        self.parent = None

    async def initialize(self):
        request = HTTPXRequest(connect_timeout=60, read_timeout=60)
        self.app = Application.builder().token(TOKEN).request(request).build()

        self.admin = AdminHandler(self.db, self.app)
        self.teacher = TeacherHandler(self.db, self.app)
        self.parent = ParentHandler(self.db, self.app)
        self.setup_handlers()

    def setup_handlers(self):
        # Авторизация
        auth_conv = ConversationHandler(
            entry_points=[CommandHandler("start", self.auth.start_command)],
            states={
                AUTH_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth.auth_login)],
                AUTH_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth.auth_password)]
            },
            fallbacks=[CommandHandler("cancel", self.auth.cancel_command)],
        )

        # Регистрация (админ)
        registration_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("^👥 Регистрация$"), self.admin.start_registration)],
            states={
                REG_ROLE: [CallbackQueryHandler(self.admin.reg_select_role)],
                REG_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.admin.reg_full_name)],
                REG_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.admin.reg_username)],
                REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.admin.reg_password)],
                REG_CLASS: [CallbackQueryHandler(self.admin.reg_select_class)],
                REG_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.admin.reg_subject)],
                REG_CHILD: [CallbackQueryHandler(self.admin.reg_select_child)],
            },
            fallbacks=[CommandHandler("cancel", self.auth.cancel_command)],
        )

        # Рассылка (админ)
        broadcast_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("^📢 Рассылка$"), self.admin.start_broadcast)],
            states={BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.admin.send_broadcast)]},
            fallbacks=[CommandHandler("cancel", self.auth.cancel_command)],
        )

        # Сообщение классному руководителю (родитель)
        parent_msg_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("^💬 Классному руководителю$"), self.parent.message_to_teacher_start)],
            states={PARENT_MESSAGE_TO_TEACHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.parent.send_message_to_teacher)]},
            fallbacks=[CommandHandler("cancel", self.auth.cancel_command)],
        )

        # Выставление оценки (учитель)
        teacher_grade_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.teacher.grade_subject_selection, pattern="^teacher_action_grade$")],
            states={TEACHER_ENTER_GRADE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.teacher.add_grade)]},
            fallbacks=[CommandHandler("cancel", self.auth.cancel_command)],
        )

        # Замечание (учитель)
        teacher_comment_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.teacher.comment_subject_selection, pattern="^teacher_action_comment$")],
            states={TEACHER_ENTER_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.teacher.add_comment)]},
            fallbacks=[CommandHandler("cancel", self.auth.cancel_command)],
        )

        # Домашнее задание (учитель)
        teacher_homework_conv = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(self.teacher.homework_class_selection, pattern="^homework_class_"),
                MessageHandler(filters.Regex("^📖 Домашнее задание$"), self.teacher.add_homework_start)
            ],
            states={TEACHER_ENTER_HOMEWORK: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.teacher.save_homework)]},
            fallbacks=[CommandHandler("cancel", self.auth.cancel_command)],
        )

        # Объявления (учитель)
        teacher_broadcast_conv = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^📢 Объявление ученикам$"), lambda u, c: self.teacher.broadcast_to_class(u, c, "students")),
                MessageHandler(filters.Regex("^📢 Объявление родителям$"), lambda u, c: self.teacher.broadcast_to_class(u, c, "parents"))
            ],
            states={TEACHER_BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.teacher.send_broadcast)]},
            fallbacks=[CommandHandler("cancel", self.auth.cancel_command)],
        )

        self.app.add_handler(auth_conv)
        self.app.add_handler(registration_conv)
        self.app.add_handler(broadcast_conv)
        self.app.add_handler(parent_msg_conv)
        self.app.add_handler(teacher_grade_conv)
        self.app.add_handler(teacher_comment_conv)
        self.app.add_handler(teacher_homework_conv)
        self.app.add_handler(teacher_broadcast_conv)
        self.app.add_handler(CommandHandler("help", self.auth.help_command))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in self.auth.user_sessions:
            await update.message.reply_text("🔒 Пожалуйста, авторизуйтесь через /start")
            return

        msg = update.message.text
        role = context.user_data.get('role')

        if msg == "🔑 Сменить пользователя":
            await self.auth.logout(update, context)
            return

        if role == 'admin':
            if msg == "📊 Статистика":
                await self.admin.show_statistics(update, context)
            elif msg == "👥 Регистрация":
                await self.admin.start_registration(update, context)
            elif msg == "📅 Расписание":
                await self.admin.show_schedule_menu(update, context)

        elif role == 'teacher' or role == 'class_teacher':
            if msg == "📚 Мои классы":
                await self.teacher.show_classes(update, context)
            elif msg == "📖 Домашнее задание":
                await self.teacher.add_homework_start(update, context)
            if role == 'class_teacher' and msg == "👥 Класс":
                await self.class_teacher_show_class_stats(update, context)

        elif role == 'student':
            if msg == "📝 Мои оценки":
                await self.student.show_grades(update, context)
            elif msg == "📅 Расписание":
                await self.student.show_schedule_menu(update, context)
            elif msg == "📖 Домашнее задание":
                await self.student.show_homework(update, context)
            elif msg == "⚠️ Замечания":
                await self.student.show_comments(update, context)

        elif role == 'parent':
            if msg == "👶 Мой ребенок":
                await self.parent.show_child_info(update, context)
            elif msg == "📊 Стат недели":
                await self.parent.show_weekly_stats(update, context)
            elif msg == "📝 Оценки ребенка":
                await self.parent.show_grades(update, context)
            elif msg == "📅 Расписание":
                await self.parent.show_schedule(update, context)

    async def class_teacher_show_class_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        class_id = context.user_data.get('class_id')
        if not class_id:
            await update.message.reply_text("❌ Ваш класс не определён.")
            return

        students = self.db.get_students_by_class(class_id)
        if not students:
            await update.message.reply_text("❌ В вашем классе нет учеников.")
            return

        text = "👥 *Список класса со средними баллами*\n\n"
        for student in students:
            avg_grade = self.db.get_average_grade_by_student(student['id'])
            text += f"• {student['full_name']} — средний балл: {avg_grade:.1f}\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        # Назад в меню
        if data == "back_to_menu":
            await self.auth.show_main_menu_from_callback(query, context)
            return

        # Отмена регистрации
        if data == "cancel_registration":
            await query.edit_message_text("❌ Регистрация отменена.")
            return

        # Админ: расписание
        if data.startswith("admin_schedule_"):
            class_id = int(data.replace("admin_schedule_", ""))
            schedule = self.db.get_schedule_by_class(class_id)
            class_info = self.db.get_class_by_id(class_id)
            if schedule:
                days = {1: "ПН", 2: "ВТ", 3: "СР", 4: "ЧТ", 5: "ПТ", 6: "СБ"}
                text = f"📅 *Расписание {class_info['name']} класса*\n\n"
                for day in range(1, 6):
                    day_schedule = [s for s in schedule if s['day_of_week'] == day]
                    if day_schedule:
                        subjects = [s['subject'] for s in sorted(day_schedule, key=lambda x: x['lesson_number'])]
                        text += f"*{days[day]}:* " + ", ".join(subjects) + "\n"
                await query.edit_message_text(text, parse_mode='Markdown')
            else:
                await query.edit_message_text("Расписание не найдено")
            return

        # Учитель: выбор класса
        if data.startswith("teacher_class_"):
            context.user_data['selected_class_id'] = int(data.replace("teacher_class_", ""))
            await self.teacher.show_students(query, context)
            return

        # Учитель: выбор ученика
        if data.startswith("teacher_student_"):
            context.user_data['selected_student_id'] = int(data.replace("teacher_student_", ""))
            await self.teacher.show_student_actions(query, context)
            return

        # Учитель: пропуск
        if data == "teacher_action_absent":
            await self.teacher.mark_absent(query, context)
            return

        # Учитель: статистика
        if data == "teacher_action_stats":
            await self.teacher.show_student_stats(query, context)
            return

        # Выбор предмета для оценки
        if data.startswith("grade_subject_"):
            subject = data.replace("grade_subject_", "")
            context.user_data['selected_subject'] = subject
            await query.edit_message_text("📝 Введите оценку (число от 1 до 5):")
            return TEACHER_ENTER_GRADE

        # Выбор предмета для замечания
        if data.startswith("comment_subject_"):
            subject = data.replace("comment_subject_", "")
            context.user_data['selected_subject'] = subject
            await query.edit_message_text("💬 Введите текст замечания:")
            return TEACHER_ENTER_COMMENT

        # Учитель: ДЗ - выбор предмета
        if data.startswith("homework_subject_"):
            subject = data.replace("homework_subject_", "")
            context.user_data['homework_subject'] = subject
            await query.edit_message_text("📖 Введите текст домашнего задания:")
            return TEACHER_ENTER_HOMEWORK

        # Ученик: расписание
        if data in ["schedule_today", "schedule_tomorrow", "schedule_week"]:
            period = data.split("_")[1]
            await self.student.show_schedule(query, period, context)
            return

    async def run(self):
        await self.initialize()
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

        bot_info = await self.app.bot.get_me()
        print(f"\n✅ Бот {bot_info.first_name} (@{bot_info.username}) запущен!")
        print("\n📋 Тестовые аккаунты:")
        print("   👑 Администратор: admin / admin")
        print("   👩‍🏫 Учитель математики: math_teacher / 123")
        print("   👩‍🏫 Учитель русского: russian_teacher / 123")
        print("   👨‍🎓 Ученик: ivanov / 123")
        print("   👪 Родитель: parent_ivanov / 123")
        print("   👔 Классный руководитель: petrova / 123")
        print("\n💡 Отправьте /start боту в Telegram")
        print("⏹️ Нажмите Ctrl+C для остановки\n")

        await asyncio.Event().wait()


async def main():
    bot = SchoolBot()
    await bot.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
