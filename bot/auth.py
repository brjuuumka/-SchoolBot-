import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from bot.constants import *

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
        telegram_id = update.effective_user.id
        logger.info(f"Команда /start от {telegram_id}")

        # Проверяем, есть ли пользователь в сессиях
        if telegram_id in self.user_sessions:
            logger.info(f"Пользователь {telegram_id} уже авторизован")
            await self.show_main_menu(update, context)
        else:
            logger.info(f"Запрашиваю логин у {telegram_id}")
            await update.message.reply_text(
                "👋 Добро пожаловать в SchoolBot!\n\nВведите ваш логин:",
                reply_markup=ReplyKeyboardMarkup([["/cancel"]], resize_keyboard=True)
            )
            return AUTH_LOGIN

    async def auth_login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        login = update.message.text
        context.user_data['login'] = login
        logger.info(f"Введен логин: {login}")
        await update.message.reply_text("Введите пароль:")
        return AUTH_PASSWORD

    async def auth_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        password = update.message.text
        login = context.user_data.get('login')
        logger.info(f"Проверка пароля для {login}")

        user = self.db.authenticate_user(login, password)

        if user:
            telegram_id = update.effective_user.id
            logger.info(f"Пользователь {login} авторизован! ID: {user['id']}, роль: {user['role']}")

            # Обновляем Telegram ID
            self.db.update_telegram_id(user['id'], telegram_id)

            # Сохраняем данные в context
            context.user_data['authenticated'] = True
            context.user_data['user_id'] = user['id']
            context.user_data['role'] = user['role']
            context.user_data['full_name'] = user['full_name']
            context.user_data['username'] = user['username']
            context.user_data['class_id'] = user.get('class_id')
            context.user_data['subject'] = user.get('subject')
            context.user_data['subjects'] = self.db.get_teacher_subjects(user['id'])

            # Сохраняем сессию
            self.user_sessions[telegram_id] = user['id']

            # Отправляем приветствие и убираем клавиатуру отмены
            await update.message.reply_text(
                f"✅ Добро пожаловать, {user['full_name']}!",
                reply_markup=ReplyKeyboardRemove()
            )

            # Показываем главное меню
            await self.show_main_menu(update, context)
            return ConversationHandler.END
        else:
            logger.warning(f"Неверный логин или пароль: {login}")
            await update.message.reply_text(
                "❌ Неверный логин или пароль.\nИспользуйте /start для входа.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает главное меню в зависимости от роли"""
        role = context.user_data.get('role')
        full_name = context.user_data.get('full_name', '')

        logger.info(f"Показываю главное меню для роли: {role}, пользователь: {full_name}")

        # Получаем название класса если есть
        class_name = ""
        if context.user_data.get('class_id'):
            class_info = self.db.get_class_by_id(context.user_data['class_id'])
            if class_info:
                class_name = class_info['name']

        # Формируем приветственное сообщение
        welcome_text = f"Здравствуйте, {full_name}!"
        if class_name:
            welcome_text += f"\n📚 Класс: {class_name}"

        # Получаем клавиатуру
        reply_markup = get_main_menu(role)

        # Отправляем сообщение с меню
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup
        )

    async def show_main_menu_from_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показывает главное меню из callback (для кнопки Назад)"""
        role = context.user_data.get('role')
        full_name = context.user_data.get('full_name', '')

        logger.info(f"Показываю главное меню из callback для роли: {role}")

        welcome_text = f"Здравствуйте, {full_name}!"

        await query.edit_message_text("🔙 Возврат в главное меню")
        await query.message.reply_text(
            welcome_text,
            reply_markup=get_main_menu(role)
        )

    async def logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        telegram_id = update.effective_user.id
        if telegram_id in self.user_sessions:
            del self.user_sessions[telegram_id]

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

    def is_authenticated(self, telegram_id: int) -> bool:
        """Проверка аутентификации"""
        return telegram_id in self.user_sessions
