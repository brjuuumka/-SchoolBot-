from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.constants import PARENT_MESSAGE_TO_TEACHER


class ParentHandler:
    def __init__(self, db, application):
        self.db = db
        self.application = application

    async def get_child(self, context):
        """Получить информацию о ребенке родителя"""
        return self.db.get_child_for_parent(context.user_data['user_id'])

    async def show_child_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает информацию о ребенке со средними баллами по предметам"""
        child = await self.get_child(context)
        if not child:
            await update.message.reply_text("❌ Ребёнок не привязан. Обратитесь к администратору.")
            return

        # Общий средний балл
        avg_grade = self.db.get_average_grade_by_student(child['id'])

        # Посещаемость
        attendance = self.db.get_attendance_by_student(child['id'])
        present_count = sum(1 for a in attendance if a['is_present']) if attendance else 0
        total_count = len(attendance) if attendance else 1

        # Оценки по предметам для детализации
        grades = self.db.get_grades_by_student(child['id'])
        subjects_avg = {}
        for g in grades:
            if g['subject'] not in subjects_avg:
                subjects_avg[g['subject']] = []
            subjects_avg[g['subject']].append(g['grade'])

        text = f"👶 *{child['full_name']}*\n"
        text += f"📚 *Класс:* {child['class_name']}\n"
        text += f"📈 *Общий средний балл:* {avg_grade:.1f}\n"
        text += f"📋 *Посещаемость:* {present_count}/{total_count} уроков\n\n"

        if subjects_avg:
            text += "📊 *Средние баллы по предметам:*\n"
            for subject, grades_list in subjects_avg.items():
                subject_avg = sum(grades_list) / len(grades_list)
                text += f"   • {subject}: {subject_avg:.1f}\n"
        else:
            text += "📝 *Оценок пока нет*"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def show_weekly_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает детальную статистику за неделю (оценки, замечания, пропуски)"""
        child = await self.get_child(context)
        if not child:
            await update.message.reply_text("❌ Ребёнок не привязан.")
            return

        week_ago = datetime.now() - timedelta(days=7)

        # Оценки за неделю
        grades = self.db.get_grades_by_student(child['id'])
        week_grades = []
        for g in grades:
            try:
                if datetime.strptime(g['date'], '%Y-%m-%d') >= week_ago:
                    week_grades.append(g)
            except:
                pass

        # Замечания за неделю
        comments = self.db.get_comments_by_student(child['id'])
        week_comments = []
        for c in comments:
            try:
                if datetime.strptime(c['date'], '%Y-%m-%d') >= week_ago:
                    week_comments.append(c)
            except:
                pass

        # Посещаемость за неделю
        attendance = self.db.get_attendance_by_student(child['id'])
        week_attendance = []
        for a in attendance:
            try:
                if datetime.strptime(a['date'], '%Y-%m-%d') >= week_ago:
                    week_attendance.append(a)
            except:
                pass

        present_count = sum(1 for a in week_attendance if a['is_present'])
        absent_count = len(week_attendance) - present_count

        # Средний балл за неделю
        avg = sum(g['grade'] for g in week_grades) / len(week_grades) if week_grades else 0

        text = f"📊 *Статистика {child['full_name']} за неделю*\n\n"
        text += f"📅 *Период:* {week_ago.strftime('%d.%m.%Y')} - {datetime.now().strftime('%d.%m.%Y')}\n\n"

        # Оценки
        text += f"📝 *Оценки:* {len(week_grades)}, средний балл: {avg:.1f}\n"
        if week_grades:
            text += "*Список оценок:*\n"
            for g in week_grades[:10]:
                text += f"   • {g['subject']}: {g['grade']} ({g['date']})\n"
        text += "\n"

        # Замечания
        text += f"⚠️ *Замечания:* {len(week_comments)}\n"
        if week_comments:
            text += "*Список замечаний:*\n"
            for c in week_comments[:5]:
                text += f"   • {c['subject']}: {c['text'][:50]}\n"
        text += "\n"

        # Посещаемость
        text += f"📋 *Посещаемость:* ✅ присутствовал: {present_count} / ❌ отсутствовал: {absent_count}"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def show_grades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает все оценки ребенка по предметам"""
        child = await self.get_child(context)
        if not child:
            await update.message.reply_text("❌ Ребёнок не привязан.")
            return

        grades = self.db.get_grades_by_student(child['id'])
        if not grades:
            await update.message.reply_text(f"📝 У {child['full_name']} пока нет оценок.")
            return

        subjects = {}
        for g in grades:
            subjects.setdefault(g['subject'], []).append(g['grade'])

        text = f"📝 *Оценки {child['full_name']}*\n\n"
        for subject, grades_list in subjects.items():
            avg = sum(grades_list) / len(grades_list)
            text += f"*{subject}*: {', '.join(map(str, grades_list))} (ср. {avg:.1f})\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def show_schedule(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показывает расписание класса ребенка"""
        child = await self.get_child(context)
        if not child or not child.get('class_id'):
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
                subjects = [s['subject'] for s in sorted(day_schedule, key=lambda x: x['lesson_number'])]
                text += f"*{days[day_num]}:* " + ", ".join(subjects) + "\n"
            else:
                text += f"*{days[day_num]}:* нет уроков\n"

        await update.message.reply_text(text, parse_mode='Markdown')

    async def message_to_teacher_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало отправки сообщения классному руководителю"""
        child = await self.get_child(context)
        if not child:
            await update.message.reply_text("❌ Ребёнок не привязан. Обратитесь к администратору.")
            return

        context.user_data['parent_child'] = child
        await update.message.reply_text(
            f"💬 *Сообщение классному руководителю*\n\n"
            f"👶 Ребёнок: {child['full_name']}\n"
            f"📚 Класс: {child['class_name']}\n\n"
            f"📝 Введите текст сообщения:",
            parse_mode='Markdown'
        )
        return PARENT_MESSAGE_TO_TEACHER

    async def send_message_to_teacher(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Отправка сообщения классному руководителю"""
        message_text = update.message.text
        child = context.user_data.get('parent_child')
        parent_name = context.user_data.get('full_name')

        if not child:
            await update.message.reply_text("❌ Ошибка: данные о ребёнке не найдены.")
            return ConversationHandler.END

        class_teacher = self.db.get_class_teacher_by_student(child['id'])

        if not class_teacher or not class_teacher.get('telegram_id'):
            await update.message.reply_text(
                "❌ Не удалось отправить сообщение. Классный руководитель не зарегистрирован в боте."
            )
            return ConversationHandler.END

        try:
            await self.application.bot.send_message(
                chat_id=class_teacher['telegram_id'],
                text=f"💬 *Сообщение от родителя*\n\n"
                     f"👪 Родитель: {parent_name}\n"
                     f"👶 Ученик: {child['full_name']}\n"
                     f"📚 Класс: {child['class_name']}\n\n"
                     f"📝 Текст:\n{message_text}",
                parse_mode='Markdown'
            )
            await update.message.reply_text("✅ Сообщение отправлено классному руководителю!")
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
            await update.message.reply_text("❌ Ошибка при отправке сообщения.")

        return ConversationHandler.END
