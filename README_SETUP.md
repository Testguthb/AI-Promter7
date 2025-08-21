# 🚀 Швидке встановлення та запуск

Цей посібник допоможе вам швидко встановити та запустити Telegram Text Processor Bot на будь-якій операційній системі.

## 📋 Передумови

### Всі системи:
- **Python 3.8+** - [Завантажити](https://www.python.org/downloads/)
- **Git** (опціонально) - для клонування репозиторію

### Отримання API ключів:
1. **Telegram Bot Token**: Створіть бота через [@BotFather](https://t.me/botfather)
2. **OpenAI API Key**: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
3. **Anthropic API Key**: [console.anthropic.com](https://console.anthropic.com/)

## 🖥️ Встановлення за операційною системою

### 🐧 Linux / 🍎 macOS

#### Метод 1: Автоматичне встановлення
```bash
# Зробити скрипт виконуваним
chmod +x install.sh

# Запустити встановлення
./install.sh
```

#### Метод 2: Універсальний лаунчер
```bash
# Запустити універсальний лаунчер
python3 launch.py
```

### 🪟 Windows

#### Метод 1: Автоматичне встановлення
1. Подвійний клік на `install.bat`
2. Або відкрийте Command Prompt та виконайте:
```cmd
install.bat
```

#### Метод 2: Універсальний лаунчер
1. Подвійний клік на `launch.py`
2. Або відкрийте Command Prompt та виконайте:
```cmd
python launch.py
```

## ⚙️ Налаштування

### 1. Налаштування .env файлу
Після встановлення відредагуйте файл `.env`:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# OpenAI Configuration  
OPENAI_API_KEY=sk-proj-abcd1234...

# Anthropic (Claude) Configuration
ANTHROPIC_API_KEY=sk-ant-api03-abcd1234...
```

### 2. Перевірка налаштувань
Переконайтеся, що всі API ключі правильно налаштовані:
- Telegram токен починається з числа і містить ":"
- OpenAI ключ починається з "sk-proj-" або "sk-"
- Anthropic ключ починається з "sk-ant-api03-"

## 🚀 Запуск бота

### Linux / macOS:
```bash
# Метод 1: Використання скрипту запуску
./start.sh

# Метод 2: Універсальний лаунчер
python3 launch.py

# Метод 3: Ручний запуск
source venv/bin/activate
python main.py
```

### Windows:
```cmd
REM Метод 1: Подвійний клік на start.bat
start.bat

REM Метод 2: Універсальний лаунчер
python launch.py

REM Метод 3: Ручний запуск
venv\Scripts\activate.bat
python main.py
```

## 🛑 Зупинка бота

### Linux / macOS:
```bash
# Метод 1: Скрипт зупинки
./stop.sh

# Метод 2: В терміналі з ботом
Ctrl+C
```

### Windows:
```cmd
REM Метод 1: Скрипт зупинки
stop.bat

REM Метод 2: В командному рядку з ботом
Ctrl+C
```

## 🔧 Структура файлів

```
telegram-bot/
├── 📁 src/                 # Вихідний код бота
├── 📄 main.py             # Головний файл запуску
├── 📄 requirements.txt    # Python залежності
├── 📄 .env               # Конфігурація (створюється автоматично)
├── 📄 .env.template      # Шаблон конфігурації
├── 📄 launch.py          # Універсальний лаунчер
├── 🐧 install.sh         # Встановлення для Linux/macOS
├── 🪟 install.bat        # Встановлення для Windows
├── 🐧 start.sh           # Запуск для Linux/macOS
├── 🪟 start.bat          # Запуск для Windows
├── 🐧 stop.sh            # Зупинка для Linux/macOS
└── 🪟 stop.bat           # Зупинка для Windows
```

## 🆘 Вирішення проблем

### Python не знайдено
- **Linux**: `sudo apt install python3 python3-pip python3-venv`
- **macOS**: `brew install python3` або завантажте з python.org
- **Windows**: Завантажте з python.org та відмітьте "Add Python to PATH"

### Помилки встановлення залежностей
```bash
# Оновіть pip
pip install --upgrade pip

# Переустановіть залежності
pip install -r requirements.txt --force-reinstall
```

### Бот не запускається
1. Перевірте .env файл
2. Перевірте інтернет з'єднання
3. Перевірте правильність API ключів
4. Подивіться логи в файлі `bot.log`

### Права доступу (Linux/macOS)
```bash
# Зробити скрипти виконуваними
chmod +x install.sh start.sh stop.sh launch.py
```

## 📞 Підтримка

Якщо у вас виникли проблеми:
1. Перевірте файл `bot.log` на наявність помилок
2. Переконайтеся, що всі API ключі правильні
3. Спробуйте переустановити залежності
4. Перевірте підключення до інтернету

## 🎯 Швидкий старт (TL;DR)

1. **Встановлення**: Запустіть `install.sh` (Linux/macOS) або `install.bat` (Windows)
2. **Налаштування**: Відредагуйте файл `.env` з вашими API ключами
3. **Запуск**: Запустіть `start.sh` (Linux/macOS) або `start.bat` (Windows)
4. **Використання**: Надішліть файл боту в Telegram

Готово! 🎉