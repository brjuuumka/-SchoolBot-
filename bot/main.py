import json
import asyncio
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, \
    ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, \
    filters, ContextTypes

TOKEN = "8637734040:AAEOJA4vQ1-Da2abanKOCVuR5ArTNESJhnc"
ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin"

# Состояния для ConversationHandler
AUTH_LOGIN, AUTH_PASSWORD = range(2)

# Данные
schedule_data = {}

users_db = {
    "admin_1": {
        "username": "admin",
        "password": "admin",
        "role": "admin",
        "full_name": "Администратор",
        "user_id": None
    }
}


class SchoolBot:
    def __init__(self, token: str):
        self.token = token
        self.application = None

    async def initialize(self):
        #Инициализация приложения
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()

    def setup_handlers(self):
        #Настройка обработчиков команд
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

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        #Обработчик команды /start
        user_id = update.effective_user.id
        context.user_data['user_id'] = user_id

        if self.is_authenticated(user_id):
            await self.show_main_menu(update, context)
        else:
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

    async def auth_login(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        #Получение логина
        login = update.message.text
        context.user_data['login'] = login

        cancel_keyboard = ReplyKeyboardMarkup(
            [[KeyboardButton("/cancel")]],
            resize_keyboard=True
        )
        await update.message.reply_text(
            "Введите пароль:",
            reply_markup=cancel_keyboard
        )
        return AUTH_PASSWORD

    async def auth_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        #Проверка пароля и авторизация
        password = update.message.text
        login = context.user_data.get('login')

        if login == ADMIN_LOGIN and password == ADMIN_PASSWORD:
            user_id = context.user_data['user_id']

            for user_data in users_db.values():
                if user_data['username'] == login:
                    user_data['user_id'] = user_id
                    break

            context.user_data['authenticated'] = True
            context.user_data['role'] = 'admin'
            context.user_data['username'] = login

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

    async def cancel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        #Отмена авторизации
        await update.message.reply_text(
            "❌ Авторизация отменена. Используйте /start для входа.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        #Команда помощи
        help_text = (
            "🤖 *SchoolBot - школьный дневник*\n\n"
            "📱 *Доступные команды:*\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать это сообщение\n"
            "/cancel - Отменить текущее действие\n\n"
            "🔑 *Тестовый доступ:*\n"
            "Логин: admin\n"
            "Пароль: admin"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        #Показывает главное меню
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

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        #Обработка текстовых сообщений
        if not self.is_authenticated(update.effective_user.id):
            await update.message.reply_text("🔒 Пожалуйста, авторизуйтесь через /start")
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

    async def show_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        #Показывает статистику
        stats = (
            "📊 *Статистика школы*\n\n"
            f"👥 *Пользователей:* {len(users_db)}\n"
            f"👨‍🎓 *Учеников:* {self.count_users_by_role('student')}\n"
            f"👨‍🏫 *Учителей:* {self.count_users_by_role('teacher')}\n"
            f"👪 *Родителей:* {self.count_users_by_role('parent')}\n"
            f"👔 *Администраторов:* {self.count_users_by_role('admin')}\n\n"
            f"📚 *Классов в расписании:* {len(schedule_data)}"
        )
        await update.message.reply_text(stats, parse_mode='Markdown')

    async def registration_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        #Меню регистрации
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

    async def broadcast_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        #Меню рассылки
        await update.message.reply_text(
            "📢 *Рассылка сообщений*\n\n"
            "Введите текст сообщения для отправки всем пользователям:",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_broadcast'] = True

    async def show_schedule_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        #Показывает меню расписания
        if not schedule_data:
            await update.message.reply_text(
                "❌ Расписание не загружено. Проверьте файл schedule.json"
            )
            return

        keyboard = []
        for class_name in schedule_data.keys():
            keyboard.append([InlineKeyboardButton(f"📖 {class_name}", callback_data=f"schedule_{class_name}")])

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "📅 *Выберите класс:*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        #Обработка inline-кнопок
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
                "Функция в разработке.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
                ])
            )

    async def show_schedule(self, query, class_name: str):
        #Показывает расписание для класса
        if class_name not in schedule_data:
            await query.edit_message_text(
                f"❌ Расписание для класса *{class_name}* не найдено.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 К списку классов", callback_data="back_to_schedule")]
                ])
            )
            return

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
                if subjects:
                    schedule_text += f"*{day_name}:*\n"
                    for i, subject in enumerate(subjects, 1):
                        schedule_text += f"{i}. {subject}\n"
                    schedule_text += "\n"

        await query.edit_message_text(
            schedule_text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 К списку классов", callback_data="back_to_schedule")]
            ])
        )

    async def show_main_menu_from_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        #Показывает главное меню из callback
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

            await query.edit_message_text("👨‍💼 *Панель администратора*\n\nВыберите действие:", parse_mode='Markdown')
            await query.message.reply_text("Главное меню:", reply_markup=reply_markup)

    async def logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        #Выход из систем
        context.user_data.clear()

        await update.message.reply_text(
            "👋 Вы вышли из системы.\nИспользуйте /start для входа.",
            reply_markup=ReplyKeyboardRemove()
        )

    def is_authenticated(self, user_id: int) -> bool:
        #Проверяет авторизацию
        for user_data in users_db.values():
            if user_data.get('user_id') == user_id:
                return True
        return False

    def count_users_by_role(self, role: str) -> int:
        #Подсчет пользователей по роли
        return sum(1 for user_data in users_db.values() if user_data.get('role') == role)

    async def run(self):
        #Запуск бота
        await self.initialize()
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        # Держим бота запущенным
        stop_signal = asyncio.Event()
        await stop_signal.wait()


def load_schedule():
    #Загружает расписание из файла
    global schedule_data

    schedule_file = Path("schedule.json")

    if not schedule_file.exists():
        default_schedule = {
            "10А": {
                "monday": ["Математика", "Русский язык", "Физика", "История", "Английский язык"],
                "tuesday": ["Литература", "Алгебра", "Химия", "Биология", "Физкультура"],
                "wednesday": ["Геометрия", "Русский язык", "Информатика", "Обществознание", "Физика"],
                "thursday": ["Алгебра", "Литература", "Английский язык", "География", "Химия"],
                "friday": ["Русский язык", "Математика", "Физика", "История", "ОБЖ"]
            }
        }

        with open(schedule_file, 'w', encoding='utf-8') as f:
            json.dump(default_schedule, f, ensure_ascii=False, indent=2)

        schedule_data = default_schedule
    else:
        with open(schedule_file, 'r', encoding='utf-8') as f:
            schedule_data = json.load(f)


async def main():
    #Главная функция
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ОШИБКА: Укажите токен бота в переменной TOKEN")
        print("📝 Получите токен у @BotFather в Telegram")
        return

    load_schedule()
    bot = SchoolBot(TOKEN)
    await bot.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
