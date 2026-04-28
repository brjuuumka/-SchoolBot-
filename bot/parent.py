from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.constants import PARENT_MESSAGE_TO_TEACHER

class ParentHandler:
    def __init__(self, db, application):
        self.db = db
        self.application = application

    async def get_child(self, context):
        return self.db.get_child_for_parent(context.user_data['user_id'])

    async def show_grades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        child = await self.get_child(context)
        if not child:
            await update.message.reply_text("❌ Ребёнок не привязан")
            return
        grades = self.db.get_grades_by_student(child['id'])
        if not grades:
            await update.message.reply_text(f"📝 У {child['full_name']} нет оценок")
            return
        subjects = {}
        for g in grades:
            subjects.setdefault(g['subject'], []).append(g['grade'])
        text = f"📝 *Оценки {child['full_name']}*\n\n"
        for s, gl in subjects.items():
            text += f"*{s}*: {', '.join(map(str, gl))} (ср. {sum(gl)/len(gl):.1f})\n"
        await update.message.reply_text(text, parse_mode='Markdown')

    async def message_to_teacher_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        child = await self.get_child(context)
        if not child:
            await update.message.reply_text("❌ Ребёнок не привязан")
            return
        context.user_data['child'] = child
        await update.message.reply_text(f"💬 Сообщение классному руководителю\nРебёнок: {child['full_name']}\n\nВведите текст:")
        return PARENT_MESSAGE_TO_TEACHER

    async def send_message_to_teacher(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        teacher = self.db.get_class_teacher_by_student(context.user_data['child']['id'])
        if teacher and teacher.get('telegram_id'):
            await self.application.bot.send_message(
                teacher['telegram_id'],
                f"💬 От родителя {context.user_data['full_name']}\n👶 {context.user_data['child']['full_name']}\n\n{update.message.text}"
            )
            await update.message.reply_text("✅ Отправлено!")
        else:
            await update.message.reply_text("❌ Учитель не зарегистрирован")
        return ConversationHandler.END