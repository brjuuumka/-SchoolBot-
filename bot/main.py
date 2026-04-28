import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from telegram.request import HTTPXRequest

from bot.datebase import Database
from bot.constants import *
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
        request = HTTPXRequest(connect_timeout=30, read_timeout=30)
        self.app = Application.builder().token(TOKEN).request(request).build()

        self.admin = AdminHandler(self.db, self.app)
        self.teacher = TeacherHandler(self.db, self.app)
        self.parent = ParentHandler(self.db, self.app)
        self.setup_handlers()

    def setup_handlers(self):
        # Авторизация
        auth_conv = ConversationHandler(
            entry_points=[CommandHandler("start", self.auth.start_command)],
            states={AUTH_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth.auth_login)],
                    AUTH_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth.auth_password)]},
            fallbacks=[CommandHandler("cancel", self.auth.cancel_command)],
        )

        # Рассылка
        broadcast_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("^📢 Рассылка$"), self.admin.start_broadcast)],
            states={BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.admin.send_broadcast)]},
            fallbacks=[CommandHandler("cancel", self.auth.cancel_command)],
        )

        # Сообщение учителю
        parent_msg_conv = ConversationHandler(
            entry_points=[
                MessageHandler(filters.Regex("^💬 Классному руководителю$"), self.parent.message_to_teacher_start)],
            states={PARENT_MESSAGE_TO_TEACHER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, self.parent.send_message_to_teacher)]},
            fallbacks=[CommandHandler("cancel", self.auth.cancel_command)],
        )

        self.app.add_handler(auth_conv)
        self.app.add_handler(broadcast_conv)
        self.app.add_handler(parent_msg_conv)
        self.app.add_handler(
            CommandHandler("help", lambda u, c: u.message.reply_text("🤖 SchoolBot\n/start - вход\n/cancel - отмена")))
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in self.auth.user_sessions:
            await update.message.reply_text("🔒 /start для входа")
            return

        msg = update.message.text
        role = context.user_data['role']

        actions = {
            'admin': {"📊 Статистика": self.admin.show_statistics},
            'teacher': {"📚 Мои классы": self.teacher.show_classes, "📖 Домашнее задание": self.teacher.add_homework},
            'class_teacher': {"📚 Мои классы": self.teacher.show_classes,
                              "📖 Домашнее задание": self.teacher.add_homework},
            'student': {"📝 Мои оценки": self.student.show_grades, "📅 Расписание": self.student.show_schedule_menu,
                        "📖 Домашнее задание": self.student.show_homework, "⚠️ Замечания": self.student.show_comments},
            'parent': {"👶 Мой ребенок": self.parent.show_child_info, "📊 Стат недели": self.parent.show_weekly_stats,
                       "📝 Оценки ребенка": self.parent.show_grades}
        }

        if msg == "🔑 Сменить пользователя":
            await self.auth.logout(update, context)
        elif action := actions.get(role, {}).get(msg):
            await action(update, context)

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        if data.startswith("class_"):
            context.user_data['selected_class'] = int(data.split("_")[1])
            await self.teacher.show_students(query, context)
        elif data.startswith("student_"):
            context.user_data['selected_student'] = int(data.split("_")[1])
            # Показать действия с учеником
        elif data in ["today", "tomorrow", "week"]:
            await self.student.show_schedule(query, data, context)

    async def run(self):
        await self.initialize()
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        print("\n✅ Бот запущен")
        print("Тестовые аккаунты: admin/admin, ivanov/123\n")
        await asyncio.Event().wait()


async def main():
    bot = SchoolBot()
    await bot.run()


if __name__ == '__main__':
    asyncio.run(main())
