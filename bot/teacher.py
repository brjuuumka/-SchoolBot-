from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.constants import TEACHER_ENTER_GRADE, TEACHER_ENTER_COMMENT, TEACHER_ENTER_HOMEWORK, TEACHER_BROADCAST_TEXT


class TeacherHandler:
    def __init__(self, db, application):
        self.db = db
        self.application = application

    # === УВЕДОМЛЕНИЯ РОДИТЕЛЕЙ ===
    async def send_notification_to_parent(self, student_id, student_name, notification_type, subject, details):
        parent = self.db.get_parent_by_student(student_id)
        if parent and parent.get('telegram_id'):
            messages = {
                'grade': f"📝 *Новая оценка*\n\n👶 Ученик: {student_name}\n📖 Предмет: {subject}\n⭐ Оценка: {details}",
                'absent': f"❌ *Пропуск урока*\n\n👶 Ученик: {student_name}\n📖 Предмет: {subject}\n📅 Дата: {datetime.now().strftime('%d.%m.%Y')}",
                'comment': f"⚠️ *Замечание*\n\n👶 Ученик: {student_name}\n📖 Предмет: {subject}\n💬 {details}"
            }
            try:
                await self.application.bot.send_message(
                    chat_id=parent['telegram_id'],
                    text=messages.get(notification_type, ""),
                    parse_mode='Markdown'
                )
            except Exception:
                pass

    # === КЛАССЫ И УЧЕНИКИ ===
    async def show_classes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        classes = self.db.get_all_classes()
        if not classes:
            await update.message.reply_text("❌ Нет созданных классов.")
            return

        keyboard = [[InlineKeyboardButton(f"📚 {cls['name']}", callback_data=f"teacher_class_{cls['id']}")] for cls in
                    classes]
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])

        await update.message.reply_text(
            "📚 *Выберите класс:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_students(self, query, context):
        class_id = context.user_data['selected_class_id']
        students = self.db.get_students_by_class(class_id)
        class_info = self.db.get_class_by_id(class_id)

        if not students:
            await query.edit_message_text(f"❌ В классе *{class_info['name']}* нет учеников.", parse_mode='Markdown')
            return

        keyboard = [[InlineKeyboardButton(f"👨‍🎓 {s['full_name']}", callback_data=f"teacher_student_{s['id']}")] for s in
                    students]
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")])

        await query.edit_message_text(
            f"📚 *Класс {class_info['name']}*\n\nВыберите ученика:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_student_actions(self, query, context):
        student_id = context.user_data['selected_student_id']
        student = self.db.get_user_by_id(student_id)

        keyboard = [
            [InlineKeyboardButton("📝 Поставить оценку", callback_data="teacher_action_grade")],
            [InlineKeyboardButton("❌ Отметить пропуск", callback_data="teacher_action_absent")],
            [InlineKeyboardButton("💬 Написать замечание", callback_data="teacher_action_comment")],
            [InlineKeyboardButton("📊 Статистика ученика", callback_data="teacher_action_stats")],
            [InlineKeyboardButton("🔙 Назад", callback_data=f"teacher_class_{context.user_data['selected_class_id']}")]
        ]

        await query.edit_message_text(
            f"👨‍🎓 *{student['full_name']}*\n\nВыберите действие:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # === ВЫБОР ПРЕДМЕТА ДЛЯ ОЦЕНКИ ===
    async def grade_subject_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор предмета для выставления оценки"""
        query = update.callback_query
        await query.answer()

        student_id = context.user_data.get('selected_student_id')
        subjects = context.user_data.get('subjects', [])

        if not subjects:
            await query.edit_message_text("❌ У вас не назначено ни одного предмета.")
            return ConversationHandler.END

        if len(subjects) == 1:
            context.user_data['selected_subject'] = subjects[0]
            await query.edit_message_text("📝 Введите оценку (число от 1 до 5):")
            return TEACHER_ENTER_GRADE

        keyboard = []
        for subject in subjects:
            keyboard.append([InlineKeyboardButton(f"📖 {subject}", callback_data=f"grade_subject_{subject}")])

        await query.edit_message_text(
            "📖 *Выберите предмет:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return TEACHER_ENTER_GRADE

    # === ВЫБОР ПРЕДМЕТА ДЛЯ ЗАМЕЧАНИЯ ===
    async def comment_subject_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор предмета для замечания"""
        query = update.callback_query
        await query.answer()

        student_id = context.user_data.get('selected_student_id')
        subjects = context.user_data.get('subjects', [])

        if not subjects:
            await query.edit_message_text("❌ У вас не назначено ни одного предмета.")
            return ConversationHandler.END

        if len(subjects) == 1:
            context.user_data['selected_subject'] = subjects[0]
            await query.edit_message_text("💬 Введите текст замечания:")
            return TEACHER_ENTER_COMMENT

        keyboard = []
        for subject in subjects:
            keyboard.append([InlineKeyboardButton(f"📖 {subject}", callback_data=f"comment_subject_{subject}")])

        await query.edit_message_text(
            "📖 *Выберите предмет:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return TEACHER_ENTER_COMMENT

    # === ОЦЕНКИ ===
    async def add_grade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            grade = int(update.message.text)
            if grade < 1 or grade > 5:
                await update.message.reply_text("❌ Оценка должна быть от 1 до 5!")
                return TEACHER_ENTER_GRADE

            student_id = context.user_data.get('selected_student_id')
            subject = context.user_data.get('selected_subject')
            teacher_id = context.user_data['user_id']

            if not student_id or not subject:
                await update.message.reply_text("❌ Ошибка: не выбран ученик или предмет.")
                return ConversationHandler.END

            student = self.db.get_user_by_id(student_id)

            self.db.add_grade(student_id, subject, grade, teacher_id)

            await self.send_notification_to_parent(student_id, student['full_name'], 'grade', subject, str(grade))

            await update.message.reply_text(
                f"✅ Оценка {grade} по предмету {subject} выставлена ученику {student['full_name']}!")

            # Очищаем временные данные
            context.user_data.pop('selected_subject', None)

            return ConversationHandler.END

        except ValueError:
            await update.message.reply_text("❌ Введите число!")
            return TEACHER_ENTER_GRADE

    # === ПРОПУСКИ ===
    async def mark_absent(self, query, context):
        student_id = context.user_data.get('selected_student_id')
        subject = context.user_data.get('selected_subject')
        class_id = context.user_data.get('selected_class_id')

        if not subject:
            subjects = context.user_data.get('subjects', [])
            if len(subjects) == 1:
                subject = subjects[0]
                context.user_data['selected_subject'] = subject
            else:
                keyboard = []
                for subj in subjects:
                    keyboard.append(
                        [InlineKeyboardButton(f"📖 {subj}", callback_data=f"teacher_absent_{student_id}_{subj}")])
                await query.edit_message_text("Выберите предмет:", reply_markup=InlineKeyboardMarkup(keyboard))
                return

        teacher_id = context.user_data['user_id']
        student = self.db.get_user_by_id(student_id)

        self.db.mark_attendance(student_id, subject, False, teacher_id)

        await self.send_notification_to_parent(student_id, student['full_name'], 'absent', subject, "")

        await query.edit_message_text(f"✅ Пропуск по предмету {subject} отмечен у ученика {student['full_name']}!")

    # === ЗАМЕЧАНИЯ ===
    async def add_comment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        comment_text = update.message.text
        student_id = context.user_data.get('selected_student_id')
        subject = context.user_data.get('selected_subject')
        teacher_id = context.user_data['user_id']

        if not student_id or not subject:
            await update.message.reply_text("❌ Ошибка: не выбран ученик или предмет.")
            return ConversationHandler.END

        student = self.db.get_user_by_id(student_id)

        self.db.add_comment(student_id, teacher_id, subject, comment_text)

        await self.send_notification_to_parent(student_id, student['full_name'], 'comment', subject, comment_text)

        await update.message.reply_text(f"✅ Замечание по предмету {subject} добавлено ученику {student['full_name']}!")

        # Очищаем временные данные
        context.user_data.pop('selected_subject', None)

        return ConversationHandler.END

    # === СТАТИСТИКА УЧЕНИКА ===
    async def show_student_stats(self, query, context):
        student_id = context.user_data.get('selected_student_id')
        subject = context.user_data.get('selected_subject')

        if not subject:
            subjects = context.user_data.get('subjects', [])
            if len(subjects) == 1:
                subject = subjects[0]
                context.user_data['selected_subject'] = subject
            else:
                keyboard = []
                for subj in subjects:
                    keyboard.append(
                        [InlineKeyboardButton(f"📖 {subj}", callback_data=f"teacher_stats_{student_id}_{subj}")])
                await query.edit_message_text("Выберите предмет:", reply_markup=InlineKeyboardMarkup(keyboard))
                return

        avg_grade = self.db.get_average_grade_by_student(student_id, subject)
        student = self.db.get_user_by_id(student_id)

        await query.edit_message_text(
            f"📊 *Статистика ученика*\n\n"
            f"👨‍🎓 {student['full_name']}\n"
            f"📖 Предмет: {subject}\n"
            f"📈 Средний балл: {avg_grade:.1f}",
            parse_mode='Markdown'
        )

    # === ДОМАШНИЕ ЗАДАНИЯ ===
    async def add_homework_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало процесса добавления домашнего задания"""
        if hasattr(update, 'callback_query') and update.callback_query:
            query = update.callback_query
            await query.answer()
            message = query.message
        else:
            message = update.message

        classes = self.db.get_all_classes()
        if not classes:
            await message.reply_text("❌ Нет классов")
            return

        keyboard = [[InlineKeyboardButton(f"📚 {c['name']}", callback_data=f"homework_class_{c['id']}")] for c in
                    classes]
        keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="cancel_registration")])

        await message.reply_text(
            "📖 *Выберите класс для домашнего задания:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def homework_class_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Выбор класса для ДЗ"""
        query = update.callback_query
        await query.answer()

        class_id = int(query.data.replace("homework_class_", ""))
        context.user_data['homework_class_id'] = class_id

        subjects = context.user_data.get('subjects', [])

        if not subjects:
            await query.edit_message_text("❌ У вас не назначено ни одного предмета.")
            return ConversationHandler.END

        if len(subjects) == 1:
            context.user_data['homework_subject'] = subjects[0]
            await query.edit_message_text("📖 Введите текст домашнего задания:")
            return TEACHER_ENTER_HOMEWORK

        keyboard = [[InlineKeyboardButton(f"📖 {s}", callback_data=f"homework_subject_{s}")] for s in subjects]
        keyboard.append([InlineKeyboardButton("🔙 Отмена", callback_data="cancel_registration")])

        await query.edit_message_text(
            "📖 *Выберите предмет:*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return TEACHER_ENTER_HOMEWORK

    async def save_homework(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сохранение домашнего задания"""
        text = update.message.text
        class_id = context.user_data.get('homework_class_id')
        subject = context.user_data.get('homework_subject')
        teacher_id = context.user_data['user_id']

        if not class_id:
            await update.message.reply_text("❌ Ошибка: класс не выбран.")
            return ConversationHandler.END

        if not subject:
            await update.message.reply_text("❌ Ошибка: предмет не выбран.")
            return ConversationHandler.END

        self.db.add_homework(class_id, subject, text, teacher_id)

        students = self.db.get_students_by_class(class_id)
        class_info = self.db.get_class_by_id(class_id)
        sent_count = 0

        for student in students:
            user = self.db.get_user_by_id(student['id'])
            if user and user.get('telegram_id'):
                try:
                    await self.application.bot.send_message(
                        chat_id=user['telegram_id'],
                        text=f"📖 *Новое домашнее задание*\n\n"
                             f"📚 Класс: {class_info['name']}\n"
                             f"📖 Предмет: {subject}\n\n"
                             f"{text}",
                        parse_mode='Markdown'
                    )
                    sent_count += 1
                except Exception:
                    pass

        await update.message.reply_text(
            f"✅ Домашнее задание добавлено!\n"
            f"📚 Класс: {class_info['name']}\n"
            f"📖 Предмет: {subject}\n"
            f"📨 Отправлено {sent_count} ученикам."
        )

        # Очищаем временные данные
        context.user_data.pop('homework_class_id', None)
        context.user_data.pop('homework_subject', None)

        return ConversationHandler.END

    # === ОБЪЯВЛЕНИЯ ===
    async def broadcast_to_class(self, update: Update, context: ContextTypes.DEFAULT_TYPE, target):
        context.user_data['broadcast_target'] = target
        await update.message.reply_text("📢 Введите текст объявления:")
        return TEACHER_BROADCAST_TEXT

    async def send_broadcast(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        target = context.user_data.get('broadcast_target')
        class_id = context.user_data.get('class_id')

        if not class_id:
            await update.message.reply_text("❌ Ваш класс не определён.")
            return ConversationHandler.END

        students = self.db.get_students_by_class(class_id)
        class_info = self.db.get_class_by_id(class_id)
        sent_count = 0

        if target == 'students':
            for student in students:
                user = self.db.get_user_by_id(student['id'])
                if user and user.get('telegram_id'):
                    try:
                        await self.application.bot.send_message(
                            chat_id=user['telegram_id'],
                            text=f"📢 *Объявление для учеников {class_info['name']} класса*\n\n{text}",
                            parse_mode='Markdown'
                        )
                        sent_count += 1
                    except Exception:
                        pass
            await update.message.reply_text(f"✅ Объявление отправлено {sent_count} ученикам!")

        elif target == 'parents':
            for student in students:
                parent = self.db.get_parent_by_student(student['id'])
                if parent and parent.get('telegram_id'):
                    try:
                        await self.application.bot.send_message(
                            chat_id=parent['telegram_id'],
                            text=f"📢 *Объявление для родителей {class_info['name']} класса*\n\n{text}",
                            parse_mode='Markdown'
                        )
                        sent_count += 1
                    except Exception:
                        pass
            await update.message.reply_text(f"✅ Объявление отправлено {sent_count} родителям!")

        return ConversationHandler.END
