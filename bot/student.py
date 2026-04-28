from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes


class StudentHandler:
    def __init__(self, db):
        self.db = db

    async def show_grades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        grades = self.db.get_grades_by_student(context.user_data['user_id'])
        if not grades:
            await update.message.reply_text("📝 Нет оценок")
            return
        subjects = {}
        for g in grades:
            subjects.setdefault(g['subject'], []).append(g['grade'])
        text = "📝 *Оценки*\n\n"
        for s, gl in subjects.items():
            text += f"*{s}*: {', '.join(map(str, gl))} (ср. {sum(gl) / len(gl):.1f})\n"
        await update.message.reply_text(text, parse_mode='Markdown')

    async def show_schedule_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("📅 Сегодня", callback_data="today")],
            [InlineKeyboardButton("📆 Завтра", callback_data="tomorrow")],
            [InlineKeyboardButton("📊 Неделя", callback_data="week")]
        ]
        await update.message.reply_text("📅 Выберите период:", reply_markup=InlineKeyboardMarkup(keyboard))

    async def show_schedule(self, query, period, context):
        schedule = self.db.get_schedule_by_class(context.user_data['class_id'])
        if not schedule:
            await query.edit_message_text("📅 Расписания нет")
            return
        days = {1: "ПН", 2: "ВТ", 3: "СР", 4: "ЧТ", 5: "ПТ"}
        today = datetime.now().isoweekday()

        if period == "today":
            day_schedule = [s for s in schedule if s['day_of_week'] == today]
            text = f"📅 *Сегодня*\n\n" + "\n".join([f"{l['lesson_number']}. {l['subject']}" for l in day_schedule])
        elif period == "tomorrow":
            tomorrow = today + 1 if today < 5 else 1
            day_schedule = [s for s in schedule if s['day_of_week'] == tomorrow]
            text = f"📅 *Завтра*\n\n" + "\n".join([f"{l['lesson_number']}. {l['subject']}" for l in day_schedule])
        else:
            text = "📅 *Неделя*\n\n"
            for d in range(1, 6):
                day_schedule = [s for s in schedule if s['day_of_week'] == d]
                text += f"*{days[d]}:* " + ", ".join([s['subject'] for s in day_schedule]) + "\n"
        await query.edit_message_text(text or "Нет уроков", parse_mode='Markdown')