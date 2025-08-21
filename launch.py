#!/usr/bin/env python3
"""
Universal launcher for Telegram Text Processor Bot
Works on Windows, macOS, and Linux
"""

import os
import sys
import platform
import subprocess
import shutil
from pathlib import Path


def print_colored(message, color='white'):
    """Print colored messages based on the platform."""
    colors = {
        'red': '\033[91m' if platform.system() != 'Windows' else '',
        'green': '\033[92m' if platform.system() != 'Windows' else '',
        'yellow': '\033[93m' if platform.system() != 'Windows' else '',
        'blue': '\033[94m' if platform.system() != 'Windows' else '',
        'white': '\033[0m' if platform.system() != 'Windows' else '',
        'reset': '\033[0m' if platform.system() != 'Windows' else ''
    }
    
    if platform.system() == 'Windows':
        # For Windows, we'll just print without colors for simplicity
        print(f"[{color.upper()}] {message}")
    else:
        print(f"{colors.get(color, '')}{message}{colors['reset']}")


def check_python():
    """Check if Python 3.8+ is installed."""
    print_colored("🔍 Перевірка Python...", 'blue')
    
    try:
        version = sys.version_info
        if version.major == 3 and version.minor >= 8:
            print_colored(f"✅ Python {version.major}.{version.minor}.{version.micro} знайдено", 'green')
            return True
        else:
            print_colored(f"❌ Потрібен Python 3.8+. Знайдено: {version.major}.{version.minor}", 'red')
            return False
    except Exception as e:
        print_colored(f"❌ Помилка перевірки Python: {e}", 'red')
        return False


def check_venv():
    """Check if virtual environment exists."""
    venv_path = Path("venv")
    if venv_path.exists():
        print_colored("✅ Віртуальне оточення знайдено", 'green')
        return True
    else:
        print_colored("❌ Віртуальне оточення не знайдено", 'red')
        return False


def check_env_file():
    """Check if .env file exists."""
    env_path = Path(".env")
    if env_path.exists():
        print_colored("✅ .env файл знайдено", 'green')
        return True
    else:
        print_colored("❌ .env файл не знайдено", 'red')
        return False


def check_requirements():
    """Check if requirements.txt exists."""
    req_path = Path("requirements.txt")
    if req_path.exists():
        print_colored("✅ requirements.txt знайдено", 'green')
        return True
    else:
        print_colored("❌ requirements.txt не знайдено", 'red')
        return False


def run_installation():
    """Run the appropriate installation script."""
    system = platform.system()
    
    print_colored(f"🔧 Запуск встановлення для {system}...", 'yellow')
    
    try:
        if system in ['Linux', 'Darwin']:  # Darwin is macOS
            if Path("install.sh").exists():
                # Make script executable
                os.chmod("install.sh", 0o755)
                result = subprocess.run(['bash', 'install.sh'], check=True)
                return result.returncode == 0
            else:
                print_colored("❌ install.sh не знайдено", 'red')
                return False
        elif system == 'Windows':
            if Path("install.bat").exists():
                result = subprocess.run(['install.bat'], shell=True, check=True)
                return result.returncode == 0
            else:
                print_colored("❌ install.bat не знайдено", 'red')
                return False
        else:
            print_colored(f"❌ Непідтримувана операційна система: {system}", 'red')
            return False
    except subprocess.CalledProcessError as e:
        print_colored(f"❌ Помилка встановлення: {e}", 'red')
        return False
    except Exception as e:
        print_colored(f"❌ Неочікувана помилка: {e}", 'red')
        return False


def run_bot():
    """Run the bot."""
    system = platform.system()
    
    print_colored("🚀 Запуск бота...", 'blue')
    
    try:
        if system in ['Linux', 'Darwin']:
            # Activate venv and run bot
            if Path("venv/bin/python").exists():
                python_path = "venv/bin/python"
            else:
                python_path = "venv/bin/python3"
            
            result = subprocess.run([python_path, 'main.py'])
            return result.returncode == 0
            
        elif system == 'Windows':
            # Activate venv and run bot
            python_path = "venv\\Scripts\\python.exe"
            if Path(python_path).exists():
                result = subprocess.run([python_path, 'main.py'])
                return result.returncode == 0
            else:
                print_colored("❌ Python у віртуальному оточенні не знайдено", 'red')
                return False
        else:
            print_colored(f"❌ Непідтримувана операційна система: {system}", 'red')
            return False
            
    except KeyboardInterrupt:
        print_colored("\n👋 Бот зупинено користувачем", 'yellow')
        return True
    except Exception as e:
        print_colored(f"❌ Помилка запуску бота: {e}", 'red')
        return False


def create_env_from_template():
    """Create .env file from template if it doesn't exist."""
    env_path = Path(".env")
    template_path = Path(".env.template")
    
    if not env_path.exists() and template_path.exists():
        print_colored("📝 Створення .env файлу з шаблону...", 'blue')
        shutil.copy(template_path, env_path)
        print_colored("✅ .env файл створено з шаблону", 'green')
        print_colored("⚠️  ВАЖЛИВО: Відредагуйте .env файл та додайте ваші API ключі!", 'yellow')
        return True
    return False


def main():
    """Main launcher function."""
    print_colored("🤖 Telegram Text Processor Bot Launcher", 'blue')
    print_colored("=" * 50, 'blue')
    print_colored(f"Операційна система: {platform.system()}", 'blue')
    print_colored(f"Архітектура: {platform.machine()}", 'blue')
    print()
    
    # Check Python
    if not check_python():
        print_colored("\n❌ Встановіть Python 3.8+ та спробуйте знову", 'red')
        input("Натисніть Enter для виходу...")
        sys.exit(1)
    
    # Check if installation is needed
    needs_installation = False
    
    if not check_venv():
        needs_installation = True
    
    if not check_env_file():
        create_env_from_template()
        if not check_env_file():
            needs_installation = True
    
    if not check_requirements():
        print_colored("❌ Файл requirements.txt не знайдено", 'red')
        input("Натисніть Enter для виходу...")
        sys.exit(1)
    
    # Run installation if needed
    if needs_installation:
        print_colored("\n🔧 Потрібне встановлення залежностей...", 'yellow')
        
        if platform.system() == 'Windows':
            response = input("Запустити встановлення? (y/n): ")
        else:
            response = input("Запустити встановлення? (y/n): ")
            
        if response.lower() in ['y', 'yes', 'так', 'т']:
            if not run_installation():
                print_colored("❌ Помилка встановлення", 'red')
                input("Натисніть Enter для виходу...")
                sys.exit(1)
        else:
            print_colored("❌ Встановлення скасовано", 'yellow')
            sys.exit(0)
    
    # Final checks before running
    print_colored("\n🔍 Фінальна перевірка...", 'blue')
    
    if not (check_venv() and check_env_file() and Path("main.py").exists()):
        print_colored("❌ Не всі компоненти готові", 'red')
        input("Натисніть Enter для виходу...")
        sys.exit(1)
    
    print_colored("✅ Всі перевірки пройдено успішно", 'green')
    print_colored("\n" + "=" * 50, 'blue')
    
    # Run the bot
    if not run_bot():
        print_colored("❌ Помилка запуску бота", 'red')
        input("Натисніть Enter для виходу...")
        sys.exit(1)
    
    print_colored("\n👋 Дякуємо за використання бота!", 'green')


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n👋 Програма перервана користувачем", 'yellow')
    except Exception as e:
        print_colored(f"\n❌ Критична помилка: {e}", 'red')
        input("Натисніть Enter для виходу...")
        sys.exit(1)