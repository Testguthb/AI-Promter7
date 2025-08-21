# Система шаблонів промтів для Telegram-бота

## Огляд функціональності

Система шаблонів дозволяє користувачам вибирати готові промти для GPT та Claude замість введення власного тексту. Особлива увага приділена GPT шаблонам з можливістю динамічної заміни історій.

## Структура файлів

### Директорії шаблонів
- `/workspace/gpt-prompt/` - шаблони для GPT з можливістю заміни історій
- `/workspace/claude-prompt/` - шаблони для Claude (без заміни історій)

### Формат шаблонів
- Файли: `.txt` формат
- Кодування: UTF-8
- Назви: `template_name.txt` (підкреслення замінюються пробілами в UI)

## Функціональність

### Загальний процес
1. Користувач завантажує файл
2. Система пропонує вибір: GPT шаблони / Claude шаблони / Власний промт
3. При виборі шаблону показується список доступних файлів
4. Для GPT шаблонів перевіряється наявність секції "INCLUDE IN STORY:"

### GPT шаблони з динамічною заміною
Якщо шаблон містить секцію `INCLUDE IN STORY:`, система:

1. **Запитує підтвердження**: "Змінити Include Story?"
2. **При "Так"**:
   - Запитує новий промт для історії
   - Генерує нову історію через GPT
   - Замінює текст після `INCLUDE IN STORY:` на нову історію
   - Показує попередній перегляд для підтвердження
3. **При "Ні"**: використовує шаблон без змін

### Claude шаблони
Готові промти для Claude без функції редагування історії. Це просто набір заздалегідь підготованих інструкцій для різних типів генерації (різні обсяги, стилі, вимоги). Одразу використовуються для генерації без додаткової обробки.

## Технічна реалізація

### Нові стани FSM
```python
waiting_for_ai_choice = State()
waiting_for_template_choice = State()
waiting_for_story_change_confirmation = State()
waiting_for_new_story_prompt = State()
waiting_for_story_generation = State()
waiting_for_final_template_confirmation = State()
```

### Ключові функції

#### `get_template_files(directory)` 
Отримує список .txt файлів з директорії шаблонів.

#### `has_include_story_section(template_content)`
Перевіряє наявність секції "INCLUDE IN STORY:" в шаблоні.

#### `replace_story_in_template(template_content, new_story)`
Замінює історію в шаблоні, зберігаючи префікс "INCLUDE IN STORY:".

#### `generate_new_story(message, state, story_prompt)`
Генерує нову історію через GPT на основі промту користувача.

### Інтеграція з існуючим workflow

Система інтегрована в існуючий процес:
- Замінює стандартний запит промту після завантаження файлу
- Зберігає результат в `user_sessions[user_id]["custom_prompt"]`
- Продовжує стандартний процес генерації outline

## Приклади шаблонів

### GPT шаблон з заміною історії
```txt
Create a revenge story outline...

INCLUDE IN STORY:
"We need to cut dead weight," my father-in-law said...

Requirements for the story...
```

### Claude шаблон
```txt
based on the outline I gave you write me a story similar to these what I attached (in language and style) 58k characters length - double check Read number of symbols CAREFULLY and DON'T change sequence of events! Please keep in mind that I want story for 58K characters!!!!!! start from hook. 58k characters mandatory. Start story with a very very powerfull and intriguing HOOK from the fist words so people sit at the end of the seat waiting to read the rest of the story...
```

## Керування шаблонами

### Додавання нових шаблонів
1. Створіть .txt файл в відповідній директорії
2. Використовуйте зрозумілу назву файлу (підкреслення стануть пробілами)
3. Для GPT: додайте секцію "INCLUDE IN STORY:" якщо потрібна заміна історії

### Редагування шаблонів
- Редагуйте файли безпосередньо в файловій системі
- Зміни застосовуються одразу без перезапуску бота

## Обробка помилок

- Відсутність файлів шаблонів - показ повідомлення про помилку
- Помилки читання файлів - логування та повідомлення користувачу
- Помилки генерації історії - можливість повторити спробу

## Інтерфейс користувача

### Кнопки вибору AI
- 🤖 GPT Шаблони
- 🧠 Claude Шаблони  
- ✏️ Власний промт

### Кнопки управління історією
- ✅ Так (змінити історію)
- ❌ Ні (залишити як є)
- 🔄 Згенерувати нову історію
- ✅ Так, підходить (підтвердити)

## Статистика та моніторинг

Інформація про шаблони додана в команду `/status`:
- Тип промту (GPT/CLAUDE/Власний)
- Назва обраного шаблону
- Стан процесу заміни історії