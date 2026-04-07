import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, \
    ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, \
    filters, ContextTypes

from bot.database import Database

TOKEN = "8637734040:AAEOJA4vQ1-Da2abanKOCVuR5ArTNESJhnc"

# Состояния для ConversationHandler
AUTH_LOGIN, AUTH_PASSWORD = range(2)

# Состояния для регистрации
REG_ROLE, REG_FULL_NAME, REG_USERNAME, REG_PASSWORD, REG_CLASS, REG_SUBJECT, REG_CHILD = range(7)

# Состояния для рассылки
BROADCAST_TEXT = 0

# Состояния для учителя
TEACHER_SELECT_CLASS, TEACHER_SELECT_STUDENT, TEACHER_ENTER_GRADE, TEACHER_ENTER_COMMENT, TEACHER_ENTER_HOMEWORK, TEACHER_SELECT_SUBJECT = range(6)


class SchoolBot:
    def __init__(self, token: str):
        self.token = token
        self.db = Database("schoolbot.db")
        self.application = None
        self.user_sessions = {}  # telegram_id -> user_id

    async def initialize(self):
        """Инициализация приложения"""
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        # Conversation для авторизации
        auth_conv = ConversationHandler(
            entry_points=[CommandHandler("start", self.start_command)],
            states={
                AUTH_LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth_login)],
                AUTH_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.auth_password)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_command)],
        )

        # Conversation для регистрации (админ)
        registration_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("^👥 Регистрация$"), self.start_registration)],
            states={
                REG_ROLE: [CallbackQueryHandler(self.reg_select_role)],
                REG_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.reg_full_name)],
                REG_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.reg_username)],
                REG_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.reg_password)],
                REG_CLASS: [CallbackQueryHandler(self.reg_select_class)],
                REG_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.reg_subject)],
                REG_CHILD: [CallbackQueryHandler(self.reg_select_child)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_command)],
        )

        # Conversation для рассылки
        broadcast_conv = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("^📢 Рассылка$"), self.start_broadcast)],
            states={
                BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.send_broadcast)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel_command)],
        )

        self.application.add_handler(auth_conv)
        self.application.add_handler(registration_conv)
        self.application.add_handler(broadcast_conv)
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        telegram_id = update.effective_user.id

        if self.is_authenticated(telegram_id):
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
        """Получение логина"""
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
        """Проверка пароля и авторизация"""
        password = update.message.text
        login = context.user_data.get('login')

        # Проверяем в БД
        user = self.db.authenticate_user(login, password)

        if user:
            telegram_id = update.effective_user.id

            # Сохраняем связь Telegram ID с пользователем
            self.db.update_telegram_id(user['id'], telegram_id)

            context.user_data['authenticated'] = True
            context.user_data['user_id'] = user['id']
            context.user_data['role'] = user['role']
            context.user_data['full_name'] = user['full_name']
            context.user_data['username'] = user['username']
            context.user_data['class_id'] = user.get('class_id')
            context.user_data['subject'] = user.get('subject')

            # Сохраняем сессию
            self.user_sessions[telegram_id] = user['id']

            await update.message.reply_text(
                f"✅ Добро пожаловать, {user['full_name']}!",
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
        """Отмена текущего действия"""
        context.user_data.clear()
        await update.message.reply_text(
            "❌ Действие отменено. Используйте /start для входа.",
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
            "📞 *При возникновении проблем:*\n"
            "Обратитесь к администратору школы"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает главное меню в зависимости от роли"""
        role = context.user_data.get('role')
        full_name = context.user_data.get('full_name', '')

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
                f"👨‍💼 *Панель администратора*\n\n"
                f"Здравствуйте, {full_name}!\n\n"
                f"Выберите действие:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        elif role == 'teacher' or role == 'class_teacher':
            keyboard = [
                [KeyboardButton("📚 Мои классы")],
                [KeyboardButton("📖 Домашнее задание")],
                [KeyboardButton("📢 Объявление")],
                [KeyboardButton("🔑 Сменить пользователя")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.message.reply_text(
                f"👩‍🏫 *Панель учителя*\n\n"
                f"Здравствуйте, {full_name}!\n"
                f"📖 Предмет: {context.user_data.get('subject', 'Не указан')}\n\n"
                f"Выберите действие:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        elif role == 'student':
            keyboard = [
                [KeyboardButton("📝 Мои оценки")],
                [KeyboardButton("📅 Расписание")],
                [KeyboardButton("📖 Домашнее задание")],
                [KeyboardButton("⚠️ Замечания")],
                [KeyboardButton("🔑 Сменить пользователя")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.message.reply_text(
                f"👨‍🎓 *Панель ученика*\n\n"
                f"Здравствуйте, {full_name}!\n\n"
                f"Выберите действие:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        elif role == 'parent':
            keyboard = [
                [KeyboardButton("👶 Мой ребенок")],
                [KeyboardButton("📊 Стат недели")],
                [KeyboardButton("📝 Оценки ребенка")],
                [KeyboardButton("📅 Расписание")],
                [KeyboardButton("🔑 Сменить пользователя")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await update.message.reply_text(
                f"👪 *Панель родителя*\n\n"
                f"Здравствуйте, {full_name}!\n\n"
                f"Выберите действие:",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        telegram_id = update.effective_user.id

        if not self.is_authenticated(telegram_id):
            await update.message.reply_text("🔒 Пожалуйста, авторизуйтесь через /start")
            return

        message = update.message.text
        role = context.user_data.get('role')

        # Администратор
        if role == 'admin':
            if message == "📊 Статистика":
                await self.show_statistics(update, context)
            elif message == "👥 Регистрация":
                # Обрабатывается отдельным ConversationHandler
                pass
            elif message == "📢 Рассылка":
                # Обрабатывается отдельным ConversationHandler
                pass
            elif message == "📅 Расписание":
                await self.show_schedule_menu(update, context)
            elif message == "🔑 Сменить пользователя":
                await self.logout(update, context)
            else:
                await update.message.reply_text("❌ Неизвестная команда. Используйте кнопки меню.")

        # Учитель
        elif role == 'teacher' or role == 'class_teacher':
            if message == "📚 Мои классы":
                await self.teacher_show_classes(update, context)
            elif message == "📖 Домашнее задание":
                await self.teacher_add_homework(update, context)
            elif message == "📢 Объявление":
                await self.teacher_broadcast_menu(update, context)
            elif message == "🔑 Сменить пользователя":
                await self.logout(update, context)

        # Ученик
        elif role == 'student':
            if message == "📝 Мои оценки":
                await self.student_show_grades(update, context)
            elif message == "📅 Расписание":
                await self.student_show_schedule(update, context)
            elif message == "📖 Домашнее задание":
                await self.student_show_homework(update, context)
            elif message == "⚠️ Замечания":
                await self.student_show_comments(update, context)
            elif message == "🔑 Сменить пользователя":
                await self.logout(update, context)

        # Родитель
        elif role == 'parent':
            if message == "👶 Мой ребенок":
                await self.parent_show_child_info(update, context)
            elif message == "📊 Стат недели":
                await self.parent_show_weekly_stats(update, context)
            elif message == "📝 Оценки ребенка":
                await self.parent_show_grades(update, context)
            elif message == "📅 Расписание":
                await self.parent_show_schedule(update, context)
            elif message == "🔑 Сменить пользователя":
                await self.logout(update, context)

    # ---------- АДМИНИСТРАТОР ----------

    async def show_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статистику из БД"""
        stats = self.db.get_school_statistics()

        stats_text = (
            "📊 *Статистика школы*\n\n"
            f"👥 *Всего пользователей:* {sum(stats['users_by_role'].values())}\n"
            f"👨‍🎓 *Учеников:* {stats['users_by_role'].get('student', 0)}\n"
            f"👨‍🏫 *Учителей:* {stats['users_by_role'].get('teacher', 0)}\n"
            f"👪 *Родителей:* {stats['users_by_role'].get('parent', 0)}\n"
            f"👔 *Классных руководителей:* {stats['users_by_role'].get('class_teacher', 0)}\n"
            f"👑 *Администраторов:* {stats['users_by_role'].get('admin', 0)}\n\n"
            f"📈 *Средний балл по школе:* {stats['avg_grade']}\n"
            f"📋 *Общая посещаемость:* {stats['attendance_rate']}%"
        )
        await update.message.reply_text(stats_text, parse_mode='Markdown')

    async def start_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало регистрации нового пользователя"""
        keyboard = [
            [InlineKeyboardButton("👨‍🎓 Ученик", callback_data="reg_student")],
            [InlineKeyboardButton("👨‍🏫 Учитель", callback_data="reg_teacher")],
            [InlineKeyboardButton("👪 Родитель", callback_data="reg_parent")],
            [InlineKeyboardButton("👔 Классный руководитель", callback_data="reg_class_teacher")],
            [InlineKeyboardButton("🔙 Отмена", callback_data="cancel_registration")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "👥 *Регистрация нового пользователя*\n\n"
            "Выберите роль:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        return REG_ROLE

    async def reg_select_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор роли при регистрации"""
        query = update.callback_query
        await query.answer()

        role = query.data.replace("reg_", "")
        context.user_data['reg_role'] = role

        await query.edit_message_text(
            f"📝 Вы выбрали роль: *{role}*\n\n"
            f"Введите ФИО пользователя:",
            parse_mode='Markdown'
        )
        return REG_FULL_NAME

    async def reg_full_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ввод ФИО"""
        context.user_data['reg_full_name'] = update.message.text

        await update.message.reply_text(
            f"🔑 Придумайте *логин* для пользователя:\n"
            f"(только латинские буквы и цифры)",
            parse_mode='Markdown'
        )
        return REG_USERNAME

    async def reg_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ввод логина"""
        username = update.message.text
        context.user_data['reg_username'] = username

        await update.message.reply_text(
            f"🔒 Придумайте *пароль* для пользователя:",
            parse_mode='Markdown'
        )
        return REG_PASSWORD

    async def reg_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ввод пароля и создание пользователя"""
        password = update.message.text
        role = context.user_data['reg_role']
        full_name = context.user_data['reg_full_name']
        username = context.user_data['reg_username']

        # Для ученика и классрука нужен класс
        if role in ['student', 'class_teacher']:
            classes = self.db.get_all_classes()
            if classes:
                keyboard = []
                for cls in classes:
                    keyboard.append([InlineKeyboardButton(cls['name'], callback_data=f"class_{cls['id']}")])
                keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="cancel_registration")])
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    f"📚 Выберите класс для *{full_name}*:",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                context.user_data['reg_password'] = password
                return REG_CLASS
            else:
                await update.message.reply_text("❌ Нет созданных классов. Сначала создайте класс.")
                return ConversationHandler.END

        # Для учителя нужен предмет
        elif role == 'teacher':
            await update.message.reply_text(
                f"📖 Введите *предмет*, который ведёт учитель:",
                parse_mode='Markdown'
            )
            context.user_data['reg_password'] = password
            return REG_SUBJECT

        # Для родителя нужен ребёнок
        elif role == 'parent':
            students = self.db.get_all_students()
            if students:
                keyboard = []
                for student in students:
                    keyboard.append([InlineKeyboardButton(student['full_name'], callback_data=f"student_{student['id']}")])
                keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="cancel_registration")])
                reply_markup = InlineKeyboardMarkup(keyboard)

                await update.message.reply_text(
                    f"👶 Выберите *ребёнка* для родителя {full_name}:",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
                context.user_data['reg_password'] = password
                return REG_CHILD
            else:
                await update.message.reply_text("❌ Нет учеников. Сначала создайте ученика.")
                return ConversationHandler.END

        # Администратор (только для теста)
        else:
            user_id = self.db.create_user(username, password, full_name, role)
            if user_id:
                await update.message.reply_text(
                    f"✅ Пользователь *{full_name}* успешно зарегистрирован!\n\n"
                    f"📋 Логин: `{username}`\n"
                    f"🔑 Пароль: `{password}`",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Ошибка: такой логин уже существует!")
            return ConversationHandler.END

    async def reg_select_class(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор класса"""
        query = update.callback_query
        await query.answer()

        class_id = int(query.data.replace("class_", ""))
        context.user_data['reg_class_id'] = class_id

        role = context.user_data['reg_role']
        username = context.user_data['reg_username']
        password = context.user_data['reg_password']
        full_name = context.user_data['reg_full_name']

        if role == 'student':
            user_id = self.db.create_user(username, password, full_name, 'student', class_id=class_id)
        else:  # class_teacher
            user_id = self.db.create_user(username, password, full_name, 'class_teacher', class_id=class_id)

        if user_id:
            await query.edit_message_text(
                f"✅ Пользователь *{full_name}* успешно зарегистрирован!\n\n"
                f"📋 Логин: `{username}`\n"
                f"🔑 Пароль: `{password}`",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Ошибка: такой логин уже существует!")

        return ConversationHandler.END

    async def reg_subject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Ввод предмета для учителя"""
        subject = update.message.text
        username = context.user_data['reg_username']
        password = context.user_data['reg_password']
        full_name = context.user_data['reg_full_name']
        role = context.user_data['reg_role']

        user_id = self.db.create_user(username, password, full_name, role, subject=subject)

        if user_id:
            await update.message.reply_text(
                f"✅ Пользователь *{full_name}* успешно зарегистрирован!\n\n"
                f"📋 Логин: `{username}`\n"
                f"🔑 Пароль: `{password}`\n"
                f"📖 Предмет: {subject}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Ошибка: такой логин уже существует!")

        return ConversationHandler.END

    async def reg_select_child(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор ребёнка для родителя"""
        query = update.callback_query
        await query.answer()

        student_id = int(query.data.replace("student_", ""))
        username = context.user_data['reg_username']
        password = context.user_data['reg_password']
        full_name = context.user_data['reg_full_name']
        role = context.user_data['reg_role']

        user_id = self.db.create_user(username, password, full_name, role)

        if user_id:
            self.db.link_parent_to_student(user_id, student_id)
            await query.edit_message_text(
                f"✅ Пользователь *{full_name}* успешно зарегистрирован!\n\n"
                f"📋 Логин: `{username}`\n"
                f"🔑 Пароль: `{password}`\n"
                f"👶 Привязан к ученику",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Ошибка: такой логин уже существует!")

        return ConversationHandler.END

    async def start_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало рассылки"""
        await update.message.reply_text(
            "📢 *Рассылка сообщений*\n\n"
            "Введите текст сообщения для отправки ВСЕМ пользователям:",
            parse_mode='Markdown'
        )
        return BROADCAST_TEXT

    async def send_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка рассылки"""
        message_text = update.message.text

        # Получаем всех пользователей с telegram_id
        users = self.db.get_all_users_with_telegram()

        sent = 0
        failed = 0

        await update.message.reply_text("⏳ Отправка сообщений...")

        for user in users:
            if user['telegram_id']:
                try:
                    await self.application.bot.send_message(
                        chat_id=user['telegram_id'],
                        text=f"📢 *Общешкольное уведомление*\n\n{message_text}",
                        parse_mode='Markdown'
                    )
                    sent += 1
                    await asyncio.sleep(0.05)  # Небольшая задержка
                except Exception:
                    failed += 1

        await update.message.reply_text(
            f"✅ Рассылка завершена!\n\n"
            f"📨 Отправлено: {sent}\n"
            f"❌ Не доставлено: {failed}"
        )
        return ConversationHandler.END

    async def show_schedule_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает меню расписания для админа"""
        classes = self.db.get_all_classes()

        if not classes:
            await update.message.reply_text("❌ Нет созданных классов.")
            return

        keyboard = []
        for cls in classes:
            keyboard.append([InlineKeyboardButton(f"📖 {cls['name']}", callback_data=f"admin_schedule_{cls['id']}")])

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "📅 *Управление расписанием*\n\nВыберите класс:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    # ---------- УЧЕНИК ----------

    async def student_show_grades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает оценки ученика"""
        user_id = context.user_data['user_id']

        grades = self.db.get_grades_by_student(user_id)

        if not grades:
            await update.message.reply_text("📝 У вас пока нет оценок.")
            return

        # Группируем по предметам
        subjects = {}
        for grade in grades:
            subject = grade['subject']
            if subject not in subjects:
                subjects[subject] = []
            subjects[subject].append(grade['grade'])

        # Формируем сообщение
        text = "📝 *Ваши оценки*\n\n"
        for subject, grades_list in subjects.items():
            avg = sum(grades_list) / len(grades_list)
            text += f"*{subject}*: {', '.join(map(str, grades_list))} (ср. {avg:.1f})\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def student_show_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает расписание ученика"""
        class_id = context.user_data.get('class_id')

        if not class_id:
            await update.message.reply_text("❌ Ваш класс не определён.")
            return

        schedule = self.db.get_schedule_by_class(class_id)

        if not schedule:
            await update.message.reply_text("📅 Расписание пока не загружено.")
            return

        days = {
            1: "Понедельник",
            2: "Вторник",
            3: "Среда",
            4: "Четверг",
            5: "Пятница",
            6: "Суббота"
        }

        text = "📅 *Ваше расписание*\n\n"
        current_day = datetime.now().weekday() + 1  # Пн=1

        # Показываем сегодня
        today_schedule = [s for s in schedule if s['day_of_week'] == current_day]
        if today_schedule:
            text += f"*Сегодня ({days[current_day]}):*\n"
            for lesson in sorted(today_schedule, key=lambda x: x['lesson_number']):
                text += f"{lesson['lesson_number']}. {lesson['subject']}\n"
            text += "\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def student_show_homework(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает домашние задания"""
        class_id = context.user_data.get('class_id')

        if not class_id:
            await update.message.reply_text("❌ Ваш класс не определён.")
            return

        homeworks = self.db.get_homeworks_by_class(class_id)

        if not homeworks:
            await update.message.reply_text("📖 Домашних заданий пока нет.")
            return

        text = "📖 *Домашние задания*\n\n"
        for hw in homeworks[:5]:  # Последние 5
            text += f"*{hw['subject']}*:\n{hw['text']}\n"
            text += f"📅 до: {hw['deadline'] if hw['deadline'] else 'не указано'}\n"
            text += f"👩‍🏫 {hw['teacher_name']}\n\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def student_show_comments(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает замечания"""
        user_id = context.user_data['user_id']

        comments = self.db.get_comments_by_student(user_id)

        if not comments:
            await update.message.reply_text("⚠️ Замечаний пока нет.")
            return

        text = "⚠️ *Ваши замечания*\n\n"
        for comment in comments[:5]:
            text += f"*{comment['subject']}* ({comment['date']}):\n"
            text += f"{comment['text']}\n"
            text += f"👩‍🏫 {comment['teacher_name']}\n\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    # ---------- РОДИТЕЛЬ ----------

    async def parent_get_child(self, context: ContextTypes.DEFAULT_TYPE):
        """Получает данные ребёнка для родителя"""
        user_id = context.user_data['user_id']
        child = self.db.get_child_for_parent(user_id)
        return child

    async def parent_show_child_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает информацию о ребёнке"""
        child = await self.parent_get_child(context)

        if not child:
            await update.message.reply_text("❌ Ребёнок не привязан. Обратитесь к администратору.")
            return

        avg_grade = self.db.get_average_grade_by_student(child['id'])
        attendance = self.db.get_attendance_by_student(child['id'])
        present_count = sum(1 for a in attendance if a['is_present'])
        total_count = len(attendance)

        text = (
            f"👶 *Информация о ребёнке*\n\n"
            f"📛 *ФИО:* {child['full_name']}\n"
            f"📚 *Класс:* {child['class_name']}\n"
            f"📈 *Средний балл:* {avg_grade:.1f}\n"
            f"📋 *Посещаемость:* {present_count}/{total_count} уроков"
        )
        await update.message.reply_text(text, parse_mode='Markdown')

    async def parent_show_weekly_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает статистику за неделю"""
        child = await self.parent_get_child(context)

        if not child:
            await update.message.reply_text("❌ Ребёнок не привязан.")
            return

        grades = self.db.get_grades_by_student(child['id'])
        comments = self.db.get_comments_by_student(child['id'])
        attendance = self.db.get_attendance_by_student(child['id'])

        # Фильтруем за последние 7 дней
        week_ago = datetime.now() - timedelta(days=7)
        week_grades = [g for g in grades if datetime.strptime(g['date'], '%Y-%m-%d') >= week_ago]

        text = f"📊 *Статистика за неделю* - {child['full_name']}\n\n"
        text += f"📝 *Оценки:* {len(week_grades)}\n"
        text += f"⚠️ *Замечания:* {len(comments)}\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def parent_show_grades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает оценки ребёнка"""
        child = await self.parent_get_child(context)

        if not child:
            await update.message.reply_text("❌ Ребёнок не привязан.")
            return

        grades = self.db.get_grades_by_student(child['id'])

        if not grades:
            await update.message.reply_text(f"📝 У {child['full_name']} пока нет оценок.")
            return

        subjects = {}
        for grade in grades:
            subject = grade['subject']
            if subject not in subjects:
                subjects[subject] = []
            subjects[subject].append(grade['grade'])

        text = f"📝 *Оценки {child['full_name']}*\n\n"
        for subject, grades_list in subjects.items():
            avg = sum(grades_list) / len(grades_list)
            text += f"*{subject}*: {', '.join(map(str, grades_list))} (ср. {avg:.1f})\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def parent_show_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает расписание класса ребёнка"""
        child = await self.parent_get_child(context)

        if not child or not child['class_id']:
            await update.message.reply_text("❌ Класс ребёнка не определён.")
            return

        schedule = self.db.get_schedule_by_class(child['class_id'])

        if not schedule:
            await update.message.reply_text("📅 Расписание пока не загружено.")
            return

        days = {1: "ПН", 2: "ВТ", 3: "СР", 4: "ЧТ", 5: "ПТ", 6: "СБ"}
        text = f"📅 *Расписание {child['class_name']} класса*\n\n"

        for day_num in range(1, 6):
            day_schedule = [s for s in schedule if s['day_of_week'] == day_num]
            if day_schedule:
                text += f"*{days[day_num]}:* "
                subjects = [s['subject'] for s in sorted(day_schedule, key=lambda x: x['lesson_number'])]
                text += ", ".join(subjects) + "\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    # ---------- УЧИТЕЛЬ ----------

    async def teacher_show_classes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает классы учителя (для упрощения - все классы)"""
        classes = self.db.get_all_classes()

        if not classes:
            await update.message.reply_text("❌ Нет созданных классов.")
            return

        keyboard = []
        for cls in classes:
            keyboard.append([InlineKeyboardButton(f"📚 {cls['name']}", callback_data=f"teacher_class_{cls['id']}")])

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "📚 *Выберите класс:*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def teacher_add_homework(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавление домашнего задания"""
        classes = self.db.get_all_classes()

        if not classes:
            await update.message.reply_text("❌ Нет созданных классов.")
            return

        keyboard = []
        for cls in classes:
            keyboard.append([InlineKeyboardButton(f"📚 {cls['name']}", callback_data=f"homework_class_{cls['id']}")])

        keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "📖 *Выберите класс для ДЗ:*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def teacher_broadcast_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню объявлений для учителя"""
        keyboard = [
            [InlineKeyboardButton("👨‍🎓 Ученикам класса", callback_data="broadcast_students")],
            [InlineKeyboardButton("👪 Родителям класса", callback_data="broadcast_parents")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "📢 *Отправить объявление*\n\n"
            "Кому отправить?",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    # ---------- ОБЩИЕ ФУНКЦИИ ----------

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка inline-кнопок"""
        query = update.callback_query
        await query.answer()

        data = query.data

        if data == "back_to_menu":
            await self.show_main_menu_from_callback(query, context)

        elif data == "cancel_registration":
            await query.edit_message_text("❌ Регистрация отменена.")
            return ConversationHandler.END

        # Расписание для админа
        elif data.startswith("admin_schedule_"):
            class_id = int(data.replace("admin_schedule_", ""))
            await self.show_schedule_for_class(query, class_id)

        # Учитель: выбор класса
        elif data.startswith("teacher_class_"):
            class_id = int(data.replace("teacher_class_", ""))
            context.user_data['selected_class_id'] = class_id
            await self.teacher_show_students(query, context)

        # Учитель: выбор ученика
        elif data.startswith("teacher_student_"):
            student_id = int(data.replace("teacher_student_", ""))
            context.user_data['selected_student_id'] = student_id
            await self.teacher_show_student_actions(query, context)

        # Учитель: поставить оценку
        elif data == "teacher_action_grade":
            await query.edit_message_text("📝 Введите оценку (число от 1 до 5):")
            context.user_data['teacher_action'] = 'grade'
            return TEACHER_ENTER_GRADE

        # Учитель: отметить пропуск
        elif data == "teacher_action_absent":
            student_id = context.user_data['selected_student_id']
            teacher_id = context.user_data['user_id']
            subject = context.user_data.get('subject', 'Общий')
            self.db.mark_attendance(student_id, subject, False, teacher_id)
            await query.edit_message_text("✅ Пропуск отмечен!")

        # Учитель: написать замечание
        elif data == "teacher_action_comment":
            await query.edit_message_text("💬 Введите текст замечания:")
            context.user_data['teacher_action'] = 'comment'
            return TEACHER_ENTER_COMMENT

        # Учитель: статистика ученика
        elif data == "teacher_action_stats":
            student_id = context.user_data['selected_student_id']
            subject = context.user_data.get('subject', 'Общий')
            avg_grade = self.db.get_average_grade_by_student(student_id, subject)

            await query.edit_message_text(
                f"📊 *Статистика ученика*\n\n"
                f"📖 Предмет: {subject}\n"
                f"📈 Средний балл: {avg_grade:.1f}",
                parse_mode='Markdown'
            )

        # Учитель: выбор класса для ДЗ
        elif data.startswith("homework_class_"):
            class_id = int(data.replace("homework_class_", ""))
            context.user_data['homework_class_id'] = class_id
            await query.edit_message_text("📖 Введите текст домашнего задания:")
            return TEACHER_ENTER_HOMEWORK

        # Учитель: рассылка
        elif data == "broadcast_students":
            context.user_data['broadcast_type'] = 'students'
            await query.edit_message_text("📢 Введите текст объявления для УЧЕНИКОВ класса:")
            return TEACHER_ENTER_HOMEWORK  # используем то же состояние

        elif data == "broadcast_parents":
            context.user_data['broadcast_type'] = 'parents'
            await query.edit_message_text("📢 Введите текст объявления для РОДИТЕЛЕЙ:")
            return TEACHER_ENTER_HOMEWORK

    async def show_main_menu_from_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показывает главное меню из callback"""
        role = context.user_data.get('role')
        full_name = context.user_data.get('full_name', '')

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

        elif role == 'teacher' or role == 'class_teacher':
            keyboard = [
                [KeyboardButton("📚 Мои классы")],
                [KeyboardButton("📖 Домашнее задание")],
                [KeyboardButton("📢 Объявление")],
                [KeyboardButton("🔑 Сменить пользователя")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

            await query.edit_message_text(f"👩‍🏫 *Панель учителя*\n\nЗдравствуйте, {full_name}!", parse_mode='Markdown')
            await query.message.reply_text("Главное меню:", reply_markup=reply_markup)

        else:
            await query.edit_message_text("🔙 Возврат в главное меню")
            await self.show_main_menu_from_callback_simple(query, context)

    async def show_main_menu_from_callback_simple(self, query, context):
        """Простое меню для остальных ролей"""
        await query.message.reply_text("Используйте кнопки меню ниже:")

    async def show_schedule_for_class(self, query, class_id: int):
        """Показывает расписание для класса"""
        schedule = self.db.get_schedule_by_class(class_id)
        class_info = self.db.get_class_by_id(class_id)

        if not schedule:
            await query.edit_message_text(f"❌ Расписание для класса *{class_info['name']}* не найдено.", parse_mode='Markdown')
            return

        days = {
            1: "Понедельник",
            2: "Вторник",
            3: "Среда",
            4: "Четверг",
            5: "Пятница",
            6: "Суббота"
        }

        text = f"📅 *Расписание для {class_info['name']} класса*\n\n"

        for day_num in range(1, 6):
            day_schedule = [s for s in schedule if s['day_of_week'] == day_num]
            if day_schedule:
                text += f"*{days[day_num]}:*\n"
                for lesson in sorted(day_schedule, key=lambda x: x['lesson_number']):
                    text += f"{lesson['lesson_number']}. {lesson['subject']}\n"
                text += "\n"

        await query.edit_message_text(text, parse_mode='Markdown')

    async def teacher_show_students(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показывает список учеников в классе"""
        class_id = context.user_data['selected_class_id']
        students = self.db.get_students_by_class(class_id)
        class_info = self.db.get_class_by_id(class_id)

        if not students:
            await query.edit_message_text(f"❌ В классе *{class_info['name']}* нет учеников.", parse_mode='Markdown')
            return

        keyboard = []
        for student in students:
            keyboard.append([InlineKeyboardButton(f"👨‍🎓 {student['full_name']}", callback_data=f"teacher_student_{student['id']}")])

        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"📚 *Класс {class_info['name']}*\n\nВыберите ученика:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def teacher_show_student_actions(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показывает действия с учеником"""
        student_id = context.user_data['selected_student_id']
        student = self.db.get_user_by_id(student_id)

        keyboard = [
            [InlineKeyboardButton("📝 Поставить оценку", callback_data="teacher_action_grade")],
            [InlineKeyboardButton("❌ Отметить пропуск", callback_data="teacher_action_absent")],
            [InlineKeyboardButton("💬 Написать замечание", callback_data="teacher_action_comment")],
            [InlineKeyboardButton("📊 Статистика ученика", callback_data="teacher_action_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data="teacher_class_" + str(context.user_data['selected_class_id']))]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"👨‍🎓 *{student['full_name']}*\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def logout(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выход из системы"""
        telegram_id = update.effective_user.id
        if telegram_id in self.user_sessions:
            del self.user_sessions[telegram_id]

        context.user_data.clear()

        await update.message.reply_text(
            "👋 Вы вышли из системы.\nИспользуйте /start для входа.",
            reply_markup=ReplyKeyboardRemove()
        )

    def is_authenticated(self, telegram_id: int) -> bool:
        """Проверяет авторизацию"""
        return telegram_id in self.user_sessions

    async def run(self):
        """Запуск бота"""
        await self.initialize()
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()

        print("✅ Бот SchoolBot запущен и работает!")
        print("📋 Тестовые аккаунты:")
        print("   👑 Админ: admin / admin")
        print("   👩‍🏫 Учитель: math_teacher / 123")
        print("   👨‍🎓 Ученик: ivanov / 123")
        print("   👪 Родитель: parent_ivanov / 123")

        # Держим бота запущенным
        stop_signal = asyncio.Event()
        await stop_signal.wait()


async def main():
    """Главная функция"""
    if TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("❌ ОШИБКА: Укажите токен бота в переменной TOKEN")
        print("📝 Получите токен у @BotFather в Telegram")
        return

    bot = SchoolBot(TOKEN)
    await bot.run()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
