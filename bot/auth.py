from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from bot.constants import *


def get_main_menu(role: str) -> ReplyKeyboardMarkup:
    menus = {
        'admin': [
            ["📊 Статистика", "👥 Регистрация"],
            ["📢 Рассылка", "📅 Расписание"],
            ["🔑 Сменить пользователя"]
        ],
        'class_teacher': [
            ["📚 Мои классы", "📖 Домашнее задание"],
            ["📢 Объявление ученикам", "📢 Объявление родителям"],
            ["👥 Класс", "🔑 Сменить пользователя"]
        ],
        'teacher': [
            ["📚 Мои классы", "📖 Домашнее задание"],
            ["📢 Объявление ученикам", "📢 Объявление родителям"],
            ["🔑 Сменить пользователя"]
        ],
        'student': [
            ["📝 Мои оценки", "📅 Расписание"],
            ["📖 Домашнее задание", "⚠️ Замечания"],
            ["🔑 Сменить пользователя"]
        ],
        'parent': [
            ["👶 Мой ребенок", "📊 Стат недели"],
            ["📝 Оценки ребенка", "📅 Расписание"],
            ["💬 Классному руководителю", "🔑 Сменить пользователя"]
        ]
    }
    return ReplyKeyboardMarkup(menus.get(role, []), resize_keyboard=True)


class AuthHandler:
    def __init__(self, db):
        self.db = db
        self.user_sessions = {}

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id in self.user_sessions:
            await self.show_main_menu(update, context)
        else:
            await update.message.reply_text(
                "👋 Добро пожаловать в SchoolBot!\n\nВведите ваш логин:",
                reply_markup=ReplyKeyboardMarkup([["/cancel"]], resize_keyboard=True)
            )
            return AUTH_LOGIN

    async def auth_login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['login'] = update.message.text
        await update.message.reply_text("Введите пароль:")
        return AUTH_PASSWORD

    async def auth_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = self.db.authenticate_user(context.user_data['login'], update.message.text)
        if user:
            self.db.update_telegram_id(user['id'], update.effective_user.id)
            context.user_data.update({
                'user_id': user['id'],
                'role': user['role'],
                'full_name': user['full_name'],
                'class_id': user.get('class_id'),
                'subjects': self.db.get_teacher_subjects(user['id'])
            })
            self.user_sessions[update.effective_user.id] = user['id']
            await update.message.reply_text(
                f"✅ Добро пожаловать, {user['full_name']}!",
                reply_markup=ReplyKeyboardRemove()
            )
            await self.show_main_menu(update, context)
        else:
            await update.message.reply_text(
                "❌ Неверный логин или пароль.\nИспользуйте /start для входа.",
                reply_markup=ReplyKeyboardRemove()
            )
        return ConversationHandler.END

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        role = context.user_data['role']
        class_name = ""
        if context.user_data.get('class_id'):
            class_name = self.db.get_class_name_by_id(context.user_data['class_id'])

        welcome_text = f"Здравствуйте, {context.user_data['full_name']}!"
        if class_name:
            welcome_text += f"\n📚 Класс: {class_name}"

        await update.message.reply_text(welcome_text, reply_markup=get_main_menu(role))

    async def logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.user_sessions.pop(update.effective_user.id, None)
        context.user_data.clear()
        await update.message.reply_text(
            "👋 Вы вышли из системы.\nИспользуйте /start для входа.",
            reply_markup=ReplyKeyboardRemove()
        )

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        await update.message.reply_text(
            "❌ Действие отменено.\nИспользуйте /start для входа.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 *SchoolBot - школьный дневник*\n\n"
            "📱 Команды:\n"
            "/start - вход в систему\n"
            "/help - помощь\n"
            "/cancel - отмена действия\n\n"
            "📞 При проблемах обратитесь к администратору",
            parse_mode='Markdown'
        )