from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

class TeacherHandler:
    def __init__(self, db, application):
        self.db = db
        self.application = application

    async def show_classes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        classes = self.db.get_all_classes()
        if not classes:
            await update.message.reply_text("❌ Нет классов")
            return
        keyboard = [[InlineKeyboardButton(f"📚 {c['name']}", callback_data=f"class_{c['id']}")] for c in classes]
        await update.message.reply_text("📚 Выберите класс:", reply_markup=InlineKeyboardMarkup(keyboard))

    async def show_students(self, query, context):
        students = self.db.get_students_by_class(context.user_data['selected_class'])
        if not students:
            await query.edit_message_text("❌ Нет учеников")
            return
        keyboard = [[InlineKeyboardButton(s['full_name'], callback_data=f"student_{s['id']}")] for s in students]
        await query.edit_message_text("Выберите ученика:", reply_markup=InlineKeyboardMarkup(keyboard))

    async def add_homework(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        classes = self.db.get_all_classes()
        if not classes:
            await update.message.reply_text("❌ Нет классов")
            return
        keyboard = [[InlineKeyboardButton(f"📚 {c['name']}", callback_data=f"hw_class_{c['id']}")] for c in classes]
        await update.message.reply_text("📖 Выберите класс:", reply_markup=InlineKeyboardMarkup(keyboard))

    async def save_homework(self, update: Update, context):
        self.db.add_homework(
            context.user_data['hw_class'], context.user_data['hw_subject'],
            update.message.text, context.user_data['user_id']
        )
        await update.message.reply_text("✅ ДЗ добавлено!")
        return -1