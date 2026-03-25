
import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, \
    ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, \
    filters, ContextTypes
from telegram.error import TimedOut, NetworkError, Conflict

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = "8637734040:AAEOJA4vQ1-Da2abanKOCVuR5ArTNESJhnc"
ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin"

# Состояния для ConversationHandler
AUTH_LOGIN, AUTH_PASSWORD = range(2)

# Временное хранение данных
users_db = {
    "admin_1": {
        "username": "admin",
        "password": "admin",
        "role": "admin",
        "full_name": "Администратор",
        "user_id": None
    }
}

# Данные для расписания
schedule_data = {
    "10А": {
        "monday": ["Математика", "Русский язык", "Физика", "История", "Английский язык"],
        "tuesday": ["Литература", "Алгебра", "Химия", "Биология", "Физкультура"],
        "wednesday": ["Геометрия", "Русский язык", "Информатика", "Обществознание", "Физика"],
        "thursday": ["Алгебра", "Литература", "Английский язык", "География", "Химия"],
        "friday": ["Русский язык", "Математика", "Физика", "История", "ОБЖ"]
    }
}


class SchoolBot:
    def __init__(self, token: str, use_proxy: bool = False, proxy_url: str = None):
        self.token = token
        self.use_proxy = use_proxy
        self.proxy_url = proxy_url
        self.application = None

    async def initialize(self):
        """Инициализация приложения с обработкой ошибок"""
        try:
            # Настройка подключения
            if self.use_proxy and self.proxy_url:
                from telegram.request import HTTPXRequest
                request = HTTPXRequest(
                    proxy=self.proxy_url,
                    connect_timeout=30.0,
                    read_timeout=30.0
                )
                builder = Application.builder().token(self.token).request(request)
            else:
                builder = Application.builder().token(self.token)

            # Увеличиваем таймауты
            builder.connect_timeout(30.0)
            builder.read_timeout(30.0)
            builder.write_timeout(30.0)
            builder.pool_timeout(30.0)

            self.application = builder.build()

            # Проверяем подключение
            await self.test_connection()

            self.setup_handlers()
            logger.info("✅ Бот успешно инициализирован")

        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            raise

    async def test_connection(self):
        """Тестирование подключения к Telegram API"""
        max_retries = 3
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                logger.info(f"Попытка подключения {attempt + 1}/{max_retries}")
                bot_info = await self.application.bot.get_me()
                logger.info(f"✅ Подключено к боту: @{bot_info.username}")
                return
            except (TimedOut, NetworkError) as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Ошибка подключения: {e}. Повтор через {retry_delay} сек...")
                    await asyncio.sleep(retry_delay)
                else:
                    raise

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # Conversation handler для авторизации
        auth_conv = ConversationHandler(
            entry_points=[CommandHandler("start", self.start_command)],
            states={
                AUTH_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth_login)],
                AUTH_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth_password)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_command)],
        )

        self.application.add_handler(auth_conv)
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Обработка ошибок
        self.application.add_error_handler(self.error_handler)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Ошибка: {context.error}")

        try:
            if update and update.effective_message:
                error_message = "⚠️ Произошла ошибка. Попробуйте позже."

                if isinstance(context.error, TimedOut):
                    error_message = "⚠️ Превышено время ожидания. Проверьте подключение к интернету."
                elif isinstance(context.error, NetworkError):
                    error_message = "⚠️ Проблемы с сетью. Проверьте интернет-соединение."
                elif isinstance(context.error, Conflict):
                    error_message = "⚠️ Бот уже запущен в другом месте."
                elif isinstance(context.error, AttributeError):
                    error_message = "⚠️ Техническая ошибка. Разработчики уже уведомлены."
                    logger.error(f"AttributeError details: {context.error}")

                await update.effective_message.reply_text(error_message)
        except Exception as e:
            logger.error(f"Ошибка в error_handler: {e}")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        try:
            user_id = update.effective_user.id
            context.user_data['user_id'] = user_id

            if self.is_authenticated(user_id):
                await self.show_main_menu(update, context)
            else:
                # Создаем клавиатуру с кнопкой отмены
                cancel_keyboard = ReplyKeyboardMarkup(
                    [[KeyboardButton("/cancel")]],
                    resize_keyboard=True
                )
                await update.message.reply_text(
                    "👋 Добро пожаловать в SchoolBot!\n\n"
                    "Пожалуйста, введите ваш логин:",
                    reply_markup=cancel_keyboard
                )
                return AUTH_LOGIN
        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")
            await update.message.reply_text("⚠️ Ошибка загрузки. Попробуйте позже.")
            return ConversationHandler.END

    async def auth_login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение логина"""
        try:
            login = update.message.text
            context.user_data['login'] = login

            # Создаем клавиатуру с кнопкой отмены
            cancel_keyboard = ReplyKeyboardMarkup(
                [[KeyboardButton("/cancel")]],
                resize_keyboard=True
            )
            await update.message.reply_text(
                "Введите пароль:",
                reply_markup=cancel_keyboard
            )
            return AUTH_PASSWORD
        except Exception as e:
            logger.error(f"Ошибка в auth_login: {e}")
            await update.message.reply_text("⚠️ Ошибка. Попробуйте /start")
            return ConversationHandler.END

    async def auth_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проверка пароля и авторизация"""
        try:
            password = update.message.text
            login = context.user_data.get('login')

            if login == ADMIN_LOGIN and password == ADMIN_PASSWORD:
                user_id = context.user_data['user_id']

                # Сохраняем информацию о пользователе
                for user_data in users_db.values():
                    if user_data['username'] == login:
                        user_data['user_id'] = user_id
                        break

                context.user_data['authenticated'] = True
                context.user_data['role'] = 'admin'
                context.user_data['username'] = login

                # Удаляем клавиатуру
                await update.message.reply_text(
                    "✅ Авторизация успешна!",
                    reply_markup=ReplyKeyboardRemove()
                )

                await self.show_main_menu(update, context)
                return ConversationHandler.END
            else:
                await update.message.reply_text(
                    "❌ Неверный логин или пароль. Попробуйте снова /start",
                    reply_markup=ReplyKeyboardRemove()
                )
                return ConversationHandler.END
        except Exception as e:
            logger.error(f"Ошибка в auth_password: {e}")
            await update.message.reply_text(
                "⚠️ Ошибка авторизации. Попробуйте /start",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отмена авторизации"""
        await update.message.reply_text(
            "❌ Авторизация отменена. Используйте /start для входа.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда помощи"""
        help_text = (
            "🤖 *SchoolBot - школьный дневник*\n\n"
            "📱 *Доступные команды:*\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать это сообщение\n"
            "/cancel - Отменить текущее действие\n\n"
            "💡 *Информация:*\n"
            "Бот позволяет отслеживать успеваемость, "
            "расписание и домашние задания.\n\n"
            "🔑 *Тестовый доступ:*\n"
            "Логин: admin\n"
            "Пароль: admin"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает главное меню в зависимости от роли"""
        try:
            role = context.user_data.get('role')

            if role == 'admin':
                keyboard = [
                    [KeyboardButton("📊 Статистика")],
                    [KeyboardButton("👥 Регистрация")],
                    [KeyboardButton("📢 Рассылка")],
                    [KeyboardButton("📅 Расписание")],
                    [KeyboardButton("🔑 Сменить пользователя")]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

                await update.message.reply_text(
                    "👨‍💼 *Панель администратора*\n\n"
                    "Выберите действие:",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Ошибка в show_main_menu: {e}")
            await update.message.reply_text("⚠️ Ошибка загрузки меню")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        try:
            if not self.is_authenticated(update.effective_user.id):
                await update.message.reply_text(
                    "🔒 Пожалуйста, авторизуйтесь через /start"
                )
                return

            message = update.message.text
            role = context.user_data.get('role')

            if role == 'admin':
                if message == "📊 Статистика":
                    await self.show_statistics(update, context)
                elif message == "👥 Регистрация":
                    await self.registration_menu(update, context)
                elif message == "📢 Рассылка":
                    await self.broadcast_menu(update, context)
                elif message == "📅 Расписание":
                    await self.show_schedule_menu(update, context)
                elif message == "🔑 Сменить пользователя":
                    await self.logout(update, context)
                else:
                    await update.message.reply_text("❌ Неизвестная команда. Используйте кнопки меню.")
        except Exception as e:
            logger.error(f"Ошибка в handle_message: {e}")
            await update.message.reply_text("⚠️ Ошибка обработки запроса")

    async def show_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статистику"""
        try:
            stats = (
                "📊 *Статистика школы*\n\n"
                f"👥 *Пользователей:* {len(users_db)}\n"
                f"👨‍🎓 *Учеников:* {self.count_users_by_role('student')}\n"
                f"👨‍🏫 *Учителей:* {self.count_users_by_role('teacher')}\n"
                f"👪 *Родителей:* {self.count_users_by_role('parent')}\n"
                f"👔 *Администраторов:* {self.count_users_by_role('admin')}\n\n"
                "📚 *Классов:* 1\n"
                "📖 *Предметов:* 11\n\n"
                "ℹ️ *Информация:*\n"
                "Бот работает в тестовом режиме"
            )
            await update.message.reply_text(stats, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Ошибка в show_statistics: {e}")
            await update.message.reply_text("⚠️ Ошибка загрузки статистики")

    async def registration_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню регистрации нового пользователя"""
        try:
            keyboard = [
                [InlineKeyboardButton("👨‍🎓 Ученик", callback_data="reg_student")],
                [InlineKeyboardButton("👨‍🏫 Учитель", callback_data="reg_teacher")],
                [InlineKeyboardButton("👪 Родитель", callback_data="reg_parent")],
                [InlineKeyboardButton("👔 Классный руководитель", callback_data="reg_class_teacher")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "👥 *Регистрация нового пользователя*\n\n"
                "Выберите роль:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка в registration_menu: {e}")
            await update.message.reply_text("⚠️ Ошибка загрузки меню регистрации")

    async def broadcast_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню рассылки"""
        await update.message.reply_text(
            "📢 *Рассылка сообщений*\n\n"
            "Введите текст сообщения для отправки всем пользователям:",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_broadcast'] = True

    async def show_schedule_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает меню расписания"""
        try:
            keyboard = [
                [InlineKeyboardButton("📖 10А класс", callback_data="schedule_10A")],
                [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "📅 *Выберите класс:*",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка в show_schedule_menu: {e}")
            await update.message.reply_text("⚠️ Ошибка загрузки расписания")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка inline-кнопок"""
        try:
            query = update.callback_query
            await query.answer()

            data = query.data

            if data == "back_to_menu":
                await self.show_main_menu_from_callback(query, context)

            elif data.startswith("schedule_"):
                class_name = data.replace("schedule_", "")
                await self.show_schedule(query, class_name)

            elif data.startswith("reg_"):
                role = data.replace("reg_", "")
                await query.edit_message_text(
                    f"🔄 Регистрация пользователя с ролью '{role}'\n\n"
                    "В разработке. Здесь будет форма регистрации.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
                    ])
                )
        except Exception as e:
            logger.error(f"Ошибка в handle_callback: {e}")
            if update.callback_query:
                await update.callback_query.message.reply_text("⚠️ Ошибка обработки")

    async def show_schedule(self, query, class_name: str):
        """Показывает расписание для класса"""
        try:
            if class_name in schedule_data:
                schedule = schedule_data[class_name]
                days = {
                    "monday": "Понедельник",
                    "tuesday": "Вторник",
                    "wednesday": "Среда",
                    "thursday": "Четверг",
                    "friday": "Пятница"
                }

                schedule_text = f"📅 *Расписание для {class_name} класса*\n\n"
                for day_key, day_name in days.items():
                    if day_key in schedule:
                        subjects = schedule[day_key]
                        schedule_text += f"*{day_name}:*\n"
                        for i, subject in enumerate(subjects, 1):
                            schedule_text += f"{i}. {subject}\n"
                        schedule_text += "\n"

                await query.edit_message_text(
                    schedule_text,
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
                    ])
                )
            else:
                await query.edit_message_text(
                    f"❌ Расписание для класса {class_name} не найдено."
                )
        except Exception as e:
            logger.error(f"Ошибка в show_schedule: {e}")
            await query.edit_message_text("⚠️ Ошибка загрузки расписания")

    async def show_main_menu_from_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показывает главное меню из callback"""
        try:
            role = context.user_data.get('role')

            if role == 'admin':
                keyboard = [
                    [KeyboardButton("📊 Статистика")],
                    [KeyboardButton("👥 Регистрация")],
                    [KeyboardButton("📢 Рассылка")],
                    [KeyboardButton("📅 Расписание")],
                    [KeyboardButton("🔑 Сменить пользователя")]
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

                await query.edit_message_text(
                    "👨‍💼 *Панель администратора*\n\n"
                    "Выберите действие:",
                    parse_mode='Markdown'
                )
                await query.message.reply_text(
                    "Главное меню:",
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Ошибка в show_main_menu_from_callback: {e}")
            await query.edit_message_text("⚠️ Ошибка загрузки меню")

    async def logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выход из системы"""
        context.user_data.clear()

        await update.message.reply_text(
            "👋 Вы вышли из системы.\n"
            "Используйте /start для входа.",
            reply_markup=ReplyKeyboardRemove()
        )

    def is_authenticated(self, user_id: int) -> bool:
        """Проверяет, авторизован ли пользователь"""
        for user_data in users_db.values():
            if user_data.get('user_id') == user_id:
                return True
        return False

    def count_users_by_role(self, role: str) -> int:
        """Подсчет пользователей по роли"""
        count = 0
        for user_data in users_db.values():
            if user_data.get('role') == role:
                count += 1
        return count

    async def run(self):
        """Запуск бота"""
        try:
            logger.info("🚀 Запуск бота...")
            await self.initialize()

            # Запускаем бота
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()

            logger.info("✅ Бот успешно запущен и готов к работе!")

            # Держим бота запущенным
            stop_signal = asyncio.Event()
            await stop_signal.wait()

        except KeyboardInterrupt:
            logger.info("🛑 Остановка бота...")
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске бота: {e}")
            raise
        finally:
            if self.application:
                await self.application.stop()
                await self.application.shutdown()


def create_schedule_file():
    """Создает файл с расписанием, если его нет"""
    schedule_file = Path("schedule.json")

    if not schedule_file.exists():
        with open(schedule_file, 'w', encoding='utf-8') as f:
            json.dump(schedule_data, f, ensure_ascii=False, indent=2)

        logger.info("✅ Создан файл расписания: schedule.json")
    else:
        # Загружаем существующее расписание
        try:
            with open(schedule_file, 'r', encoding='utf-8') as f:
                loaded_schedule = json.load(f)
                schedule_data.update(loaded_schedule)
            logger.info("✅ Загружено расписание из файла")
        except Exception as e:
            logger.error(f"Ошибка загрузки расписания: {e}")

    return schedule_file


async def main():
    """Главная функция"""
    logger.info("🚀 Запуск SchoolBot...")

    # Создаем файл расписания
    create_schedule_file()

    # Проверяем наличие токена
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ ОШИБКА: Необходимо указать токен бота в переменной TOKEN")
        logger.info("📝 Получите токен у @BotFather в Telegram")
        return

    # Создаем и запускаем бота
    bot = SchoolBot(TOKEN)

    try:
        await bot.run()
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")


if __name__ == '__main__':
    # Запуск с правильным event loop для Windows
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")