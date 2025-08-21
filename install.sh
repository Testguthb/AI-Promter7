#!/bin/bash
# Installation script for Linux/macOS - Telegram Text Processor Bot
# Цей скрипт встановлює всі необхідні залежності та налаштовує бота

set -e  # Exit on any error

echo "🤖 Встановлення Telegram Text Processor Bot..."
echo "================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.8+ is installed
check_python() {
    print_status "Перевірка версії Python..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
            print_success "Python $PYTHON_VERSION знайдено"
            PYTHON_CMD="python3"
        else
            print_error "Потрібен Python 3.8 або новіший. Знайдено: $PYTHON_VERSION"
            exit 1
        fi
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
            print_success "Python $PYTHON_VERSION знайдено"
            PYTHON_CMD="python"
        else
            print_error "Потрібен Python 3.8 або новіший. Знайдено: $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python не знайдено. Будь ласка, встановіть Python 3.8+"
        
        # Suggest installation commands for different systems
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            echo "Для Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip python3-venv"
            echo "Для CentOS/RHEL: sudo yum install python3 python3-pip"
            echo "Для Arch: sudo pacman -S python python-pip"
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            echo "Для macOS: brew install python3"
            echo "Або завантажте з https://www.python.org/downloads/"
        fi
        exit 1
    fi
}

# Check if pip is available
check_pip() {
    print_status "Перевірка pip..."
    
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
        print_success "pip3 знайдено"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
        print_success "pip знайдено"
    else
        print_error "pip не знайдено. Встановлюю pip..."
        
        if [[ "$OSTYPE" == "linux-gnu"* ]]; then
            if command -v apt &> /dev/null; then
                sudo apt update && sudo apt install python3-pip -y
            elif command -v yum &> /dev/null; then
                sudo yum install python3-pip -y
            elif command -v pacman &> /dev/null; then
                sudo pacman -S python-pip --noconfirm
            fi
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            $PYTHON_CMD -m ensurepip --upgrade
        fi
        
        PIP_CMD="pip3"
    fi
}

# Create virtual environment
create_venv() {
    print_status "Створення віртуального оточення..."
    
    if [ -d "venv" ]; then
        print_warning "Віртуальне оточення вже існує. Видаляю старе..."
        rm -rf venv
    fi
    
    $PYTHON_CMD -m venv venv
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip in virtual environment
    pip install --upgrade pip
    
    print_success "Віртуальне оточення створено"
}

# Install dependencies
install_dependencies() {
    print_status "Встановлення залежностей..."
    
    if [ ! -f "requirements.txt" ]; then
        print_error "Файл requirements.txt не знайдено!"
        exit 1
    fi
    
    # Install requirements
    pip install -r requirements.txt
    
    print_success "Всі залежності встановлено"
}

# Create .env file template
create_env_template() {
    print_status "Створення шаблону .env файлу..."
    
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Anthropic (Claude) Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO

# Optional: Bot settings
MAX_FILE_SIZE_MB=10
MAX_ATTEMPTS=20
EOF
        print_success "Створено .env файл. Будь ласка, заповніть ваші API ключі!"
        print_warning "ВАЖЛИВО: Відредагуйте файл .env та додайте ваші справжні API ключі"
    else
        print_warning ".env файл вже існує. Пропускаю створення шаблону."
    fi
}

# Create startup script
create_startup_script() {
    print_status "Створення скрипту запуску..."
    
    cat > start.sh << 'EOF'
#!/bin/bash
# Startup script for Telegram Text Processor Bot

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_status "🚀 Запуск Telegram Text Processor Bot..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_error "Віртуальне оточення не знайдено. Запустіть спочатку install.sh"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env файл не знайдено. Створіть його або запустіть install.sh"
    exit 1
fi

# Activate virtual environment
print_status "Активація віртуального оточення..."
source venv/bin/activate

# Check if main.py exists
if [ ! -f "main.py" ]; then
    print_error "main.py не знайдено!"
    exit 1
fi

print_success "Запуск бота..."
echo "Для зупинки бота натисніть Ctrl+C"
echo "=========================================="

# Run the bot
python main.py
EOF

    chmod +x start.sh
    print_success "Скрипт запуску створено (start.sh)"
}

# Create stop script
create_stop_script() {
    print_status "Створення скрипту зупинки..."
    
    cat > stop.sh << 'EOF'
#!/bin/bash
# Stop script for Telegram Text Processor Bot

echo "🛑 Зупинка Telegram Text Processor Bot..."

# Find and kill bot processes
PIDS=$(pgrep -f "python.*main.py" || true)

if [ -z "$PIDS" ]; then
    echo "Бот не запущений"
else
    echo "Знайдено процеси бота: $PIDS"
    echo "Зупинка процесів..."
    kill $PIDS
    sleep 2
    
    # Force kill if still running
    PIDS=$(pgrep -f "python.*main.py" || true)
    if [ ! -z "$PIDS" ]; then
        echo "Примусова зупинка процесів..."
        kill -9 $PIDS
    fi
    
    echo "✅ Бот зупинено"
fi
EOF

    chmod +x stop.sh
    print_success "Скрипт зупинки створено (stop.sh)"
}

# Main installation process
main() {
    echo "Початок встановлення..."
    echo
    
    check_python
    check_pip
    create_venv
    install_dependencies
    create_env_template
    create_startup_script
    create_stop_script
    
    echo
    echo "================================================"
    print_success "✅ Встановлення завершено успішно!"
    echo
    echo "Наступні кроки:"
    echo "1. Відредагуйте файл .env та додайте ваші API ключі"
    echo "2. Запустіть бота командою: ./start.sh"
    echo "3. Для зупинки бота: ./stop.sh або Ctrl+C"
    echo
    print_warning "ВАЖЛИВО: Не забудьте налаштувати .env файл!"
}

# Run main function
main