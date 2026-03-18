# -SchoolBot-
Разработка Telegram-бота «SchoolBot — школьный дневник»
<img width="427" height="474" alt="image" src="https://github.com/user-attachments/assets/baaae608-15a1-4877-8fda-3b7e38f929f2" />

SchoolBot/
├── .github/
│   └── workflows/
│       └── deploy.yml              # Автоматический деплой
│
├── bot/                             # Основной код бота
│   ├── handlers/                    # Обработчики команд по ролям
│   │   ├── student.py
│   │   ├── parent.py
│   │   ├── teacher.py
│   │   ├── class_teacher.py
│   │   └── admin.py
│   ├── keyboards.py                 # Все клавиатуры (Reply/Inline)
│   ├── database.py                   # Работа с БД (подключение, запросы)
│   ├── models.py                      # Модели данных
│   ├── utils.py                       # Вспомогательные функции
│   └── main.py                         # Точка входа
│
├── docs/                             # Документация
│   ├── user_guide.md                  # Инструкции для пользователей
│   └── schema.sql                      # Структура БД
│
├── scripts/                          # Вспомогательные скрипты
│   ├── deploy.sh                       # Деплой на сервер
│   └── seed_data.py                     # Тестовые данные
│
├── requirements.txt                    # Все зависимости
└── README.md                           # Описание проекта
