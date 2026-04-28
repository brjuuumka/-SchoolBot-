import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.constants import *


class AdminHandler:
    def __init__(self, db, application):
        self.db = db
        self.application = application

    async def show_statistics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        stats = self.db.get_school_statistics()
        text = (
            "📊 *Статистика школы*\n\n"
            f"👥 Всего пользователей: {sum(stats['users_by_role'].values())}\n"
            f"👨‍🎓 Учеников: {stats['users_by_role'].get('student', 0)}\n"
            f"👨‍🏫 Учителей: {stats['users_by_role'].get('teacher', 0)}\n"
            f"👪 Родителей: {stats['users_by_role'].get('parent', 0)}\n"
            f"👔 Классных руководителей: {stats['users_by_role'].get('class_teacher', 0)}\n"
            f"👑 Администраторов: {stats['users_by_role'].get('admin', 0)}\n\n"
            f"📈 Средний балл по школе: {stats['avg_grade']}\n"
            f"📋 Общая посещаемость: {stats['attendance_rate']}%"
        )
        await update.message.reply_text(text, parse_mode='Markdown')

    async def start_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("👨‍🎓 Ученик", callback_data="reg_student")],
            [InlineKeyboardButton("👨‍🏫 Учитель", callback_data="reg_teacher")],
            [InlineKeyboardButton("👪 Родитель", callback_data="reg_parent")],
            [InlineKeyboardButton("👔 Классный руководитель", callback_data="reg_class_teacher")],
            [InlineKeyboardButton("🔙 Отмена", callback_data="cancel_registration")]
        ]
        await update.message.reply_text(
            "👥 *Регистрация нового пользователя*\n\nВыберите роль:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return REG_ROLE

    async def reg_select_role(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        role = query.data.replace("reg_", "")
        context.user_data['reg_role'] = role

        await query.edit_message_text(
            f"📝 Вы выбрали роль: *{role}*\n\nВведите ФИО пользователя:",
            parse_mode='Markdown'
        )
        return REG_FULL_NAME

    async def reg_full_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['reg_full_name'] = update.message.text
        await update.message.reply_text(
            "🔑 Придумайте *логин* для пользователя:\n(только латинские буквы и цифры)",
            parse_mode='Markdown'
        )
        return REG_USERNAME

    async def reg_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['reg_username'] = update.message.text
        await update.message.reply_text("🔒 Придумайте *пароль* для пользователя:", parse_mode='Markdown')
        return REG_PASSWORD

    async def reg_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        password = update.message.text
        role = context.user_data['reg_role']
        full_name = context.user_data['reg_full_name']
        username = context.user_data['reg_username']

        context.user_data['reg_password'] = password

        if role in ['student', 'class_teacher']:
            classes = self.db.get_all_classes()
            if classes:
                keyboard = [[InlineKeyboardButton(cls['name'], callback_data=f"class_{cls['id']}")] for cls in classes]
                keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="cancel_registration")])
                await update.message.reply_text(
                    f"📚 Выберите класс для *{full_name}*:",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return REG_CLASS
            else:
                await update.message.reply_text("❌ Нет созданных классов. Сначала создайте класс.")
                return ConversationHandler.END

        elif role == 'teacher':
            await update.message.reply_text(
                "📖 Введите *предмет*, который ведёт учитель (если несколько - через запятую):",
                parse_mode='Markdown'
            )
            return REG_SUBJECT

        elif role == 'parent':
            students = self.db.get_all_students()
            if students:
                keyboard = [[InlineKeyboardButton(s['full_name'], callback_data=f"student_{s['id']}")] for s in
                            students]
                keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="cancel_registration")])
                await update.message.reply_text(
                    f"👶 Выберите *ребёнка* для родителя {full_name}:",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return REG_CHILD
            else:
                await update.message.reply_text("❌ Нет учеников. Сначала создайте ученика.")
                return ConversationHandler.END

        else:
            user_id = self.db.create_user(username, password, full_name, role)
            if user_id:
                await update.message.reply_text(
                    f"✅ Пользователь *{full_name}* успешно зарегистрирован!\n\n"
                    f"📋 Логин: `{username}`\n🔑 Пароль: `{password}`",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Ошибка: такой логин уже существует!")
            return ConversationHandler.END

    async def reg_select_class(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        class_id = int(query.data.replace("class_", ""))
        role = context.user_data['reg_role']
        username = context.user_data['reg_username']
        password = context.user_data['reg_password']
        full_name = context.user_data['reg_full_name']

        if role == 'student':
            user_id = self.db.create_user(username, password, full_name, 'student', class_id=class_id)
        else:
            user_id = self.db.create_user(username, password, full_name, 'class_teacher', class_id=class_id)

        if user_id:
            await query.edit_message_text(
                f"✅ Пользователь *{full_name}* успешно зарегистрирован!\n\n"
                f"📋 Логин: `{username}`\n🔑 Пароль: `{password}`",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Ошибка: такой логин уже существует!")

        return ConversationHandler.END

    async def reg_subject(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        subjects = update.message.text
        username = context.user_data['reg_username']
        password = context.user_data['reg_password']
        full_name = context.user_data['reg_full_name']
        role = context.user_data['reg_role']

        user_id = self.db.create_user(username, password, full_name, role, subject=subjects)

        if user_id:
            await update.message.reply_text(
                f"✅ Пользователь *{full_name}* успешно зарегистрирован!\n\n"
                f"📋 Логин: `{username}`\n🔑 Пароль: `{password}`\n📖 Предмет(ы): {subjects}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Ошибка: такой логин уже существует!")

        return ConversationHandler.END

    async def reg_select_child(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                f"📋 Логин: `{username}`\n🔑 Пароль: `{password}`\n👶 Привязан к ученику",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Ошибка: такой логин уже существует!")

        return ConversationHandler.END

    async def start_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📢 *Общешкольная рассылка*\n\nВведите текст сообщения для отправки ВСЕМ пользователям:",
            parse_mode='Markdown'
        )
        return BROADCAST_TEXT

    async def send_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_text = update.message.text
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
                    await asyncio.sleep(0.05)
                except Exception:
                    failed += 1

        await update.message.reply_text(f"✅ Рассылка завершена!\n\n📨 Отправлено: {sent}\n❌ Не доставлено: {failed}")
        return ConversationHandler.END

    async def show_schedule_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        classes = self.db.get_all_classes()
        if not classes:
            await update.message.reply_text("❌ Нет созданных классов.")
            return

        keyboard = [[InlineKeyboardButton(f"📖 {cls['name']}", callback_data=f"admin_schedule_{cls['id']}")] for cls in
                    classes]
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])

        await update.message.reply_text(
            "📅 *Управление расписанием*\n\nВыберите класс:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )