@echo off
REM Installation script for Windows - Telegram Text Processor Bot
REM Цей скрипт встановлює всі необхідні залежності та налаштовує бота

setlocal enabledelayedexpansion
chcp 65001 >nul

echo 🤖 Встановлення Telegram Text Processor Bot...
echo ================================================
echo.

REM Check if Python is installed
echo [INFO] Перевірка версії Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python не знайдено!
    echo.
    echo Будь ласка, встановіть Python 3.8+ з https://www.python.org/downloads/
    echo Під час встановлення обов'язково відмітьте "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [SUCCESS] Python %PYTHON_VERSION% знайдено

REM Check Python version (basic check for 3.x)
echo %PYTHON_VERSION% | findstr /R "^3\." >nul
if errorlevel 1 (
    echo [ERROR] Потрібен Python 3.8 або новіший. Знайдено: %PYTHON_VERSION%
    pause
    exit /b 1
)

REM Check if pip is available
echo [INFO] Перевірка pip...
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip не знайдено!
    echo Переустановіть Python з https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [SUCCESS] pip знайдено

REM Remove old virtual environment if exists
if exist "venv" (
    echo [WARNING] Віртуальне оточення вже існує. Видаляю старе...
    rmdir /s /q "venv"
)

REM Create virtual environment
echo [INFO] Створення віртуального оточення...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Не вдалося створити віртуальне оточення
    pause
    exit /b 1
)

REM Activate virtual environment and install dependencies
echo [INFO] Активація віртуального оточення та встановлення залежностей...
call venv\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip

REM Check if requirements.txt exists
if not exist "requirements.txt" (
    echo [ERROR] Файл requirements.txt не знайдено!
    pause
    exit /b 1
)

REM Install requirements
echo [INFO] Встановлення залежностей...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Помилка встановлення залежностей
    pause
    exit /b 1
)
echo [SUCCESS] Всі залежності встановлено

REM Create .env file template if it doesn't exist
echo [INFO] Створення шаблону .env файлу...
if not exist ".env" (
    (
        echo # Telegram Bot Configuration
        echo TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
        echo.
        echo # OpenAI Configuration
        echo OPENAI_API_KEY=your_openai_api_key_here
        echo.
        echo # Anthropic ^(Claude^) Configuration
        echo ANTHROPIC_API_KEY=your_anthropic_api_key_here
        echo.
        echo # Optional: Logging level ^(DEBUG, INFO, WARNING, ERROR^)
        echo LOG_LEVEL=INFO
        echo.
        echo # Optional: Bot settings
        echo MAX_FILE_SIZE_MB=10
        echo MAX_ATTEMPTS=20
    ) > .env
    echo [SUCCESS] Створено .env файл. Будь ласка, заповніть ваші API ключі!
    echo [WARNING] ВАЖЛИВО: Відредагуйте файл .env та додайте ваші справжні API ключі
) else (
    echo [WARNING] .env файл вже існує. Пропускаю створення шаблону.
)

REM Create startup batch file
echo [INFO] Створення скрипту запуску...
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo setlocal enabledelayedexpansion
    echo.
    echo echo 🚀 Запуск Telegram Text Processor Bot...
    echo echo ==========================================
    echo.
    echo REM Check if virtual environment exists
    echo if not exist "venv" ^(
    echo     echo [ERROR] Віртуальне оточення не знайдено. Запустіть спочатку install.bat
    echo     pause
    echo     exit /b 1
    echo ^)
    echo.
    echo REM Check if .env file exists
    echo if not exist ".env" ^(
    echo     echo [ERROR] .env файл не знайдено. Створіть його або запустіть install.bat
    echo     pause
    echo     exit /b 1
    echo ^)
    echo.
    echo REM Check if main.py exists
    echo if not exist "main.py" ^(
    echo     echo [ERROR] main.py не знайдено!
    echo     pause
    echo     exit /b 1
    echo ^)
    echo.
    echo echo [INFO] Активація віртуального оточення...
    echo call venv\Scripts\activate.bat
    echo.
    echo echo [SUCCESS] Запуск бота...
    echo echo Для зупинки бота натисніть Ctrl+C
    echo echo ==========================================
    echo echo.
    echo.
    echo REM Run the bot
    echo python main.py
    echo.
    echo echo.
    echo echo Бот зупинено. Натисніть будь-яку клавішу для закриття...
    echo pause ^>nul
) > start.bat
echo [SUCCESS] Скрипт запуску створено (start.bat)

REM Create stop batch file
echo [INFO] Створення скрипту зупинки...
(
    echo @echo off
    echo chcp 65001 ^>nul
    echo echo 🛑 Зупинка Telegram Text Processor Bot...
    echo.
    echo REM Kill Python processes running main.py
    echo tasklist /FI "IMAGENAME eq python.exe" /FO CSV 2^>NUL ^| find /I "main.py" ^>NUL
    echo if not errorlevel 1 ^(
    echo     echo Знайдено процеси бота. Зупинка...
    echo     taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq main.py*" 2^>NUL
    echo     taskkill /F /IM python.exe /FI "COMMANDLINE eq *main.py*" 2^>NUL
    echo     echo ✅ Бот зупинено
    echo ^) else ^(
    echo     echo Бот не запущений
    echo ^)
    echo.
    echo pause
) > stop.bat
echo [SUCCESS] Скрипт зупинки створено (stop.bat)

REM Deactivate virtual environment
deactivate

echo.
echo ================================================
echo [SUCCESS] ✅ Встановлення завершено успішно!
echo.
echo Наступні кроки:
echo 1. Відредагуйте файл .env та додайте ваші API ключі
echo 2. Запустіть бота подвійним кліком на start.bat
echo 3. Для зупинки бота: запустіть stop.bat або натисніть Ctrl+C
echo.
echo [WARNING] ВАЖЛИВО: Не забудьте налаштувати .env файл!
echo.
pause