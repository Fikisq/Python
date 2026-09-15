# Практическая работа №1 — вариант 13, этап 1

**Выполнил:** Кужугет Максим Сергеевич

**Группа:** ИКБО-71-24

## Описание

Программа реализует модель доступа к данным в памяти. Записи таблиц
`Agent`, `Command` и `Result` представлены именованными кортежами
`NamedTuple`. Данные не сохраняются на диск.

Связи между таблицами:

- `Command.agent` ссылается на `Agent.key`;
- `Result.command` ссылается на `Command.key`.

Модель проверяет уникальность ключей и не позволяет удалить запись, на
которую ссылается другая таблица.

## Структура проекта

```text
.
├── src/
│   └── main.py
├── tests/
│   └── test_main.py
├── .gitignore
├── README.md
└── run.bat
```

Сторонние библиотеки не используются. Требуется Python 3.10 или новее.

## Операции модели

Класс `DataModel` хранит три таблицы и предоставляет 13 требуемых
операций:

| Таблица | Создание | Получение | Изменение | Удаление |
|---|---|---|---|---|
| Agent | `create_agent` | `get_agents` | `update_agent` | `delete_agent` |
| Command | `create_command` | `get_commands` | `update_command` | `delete_command` |
| Result | `create_result` | `get_results` | `update_result` | `delete_result` |

Метод `get_recent_cache` выполняет формулу из задания:

1. выбирает команды не старше шести минут;
2. соединяет их с результатами по `Command.key = Result.command`;
3. возвращает пары `(Command.tags, Result.cache_hit)`.

Соединение левое внешнее: если у команды нет результата, вместо
`cache_hit` возвращается `None`. Необязательный аргумент `now` задаёт
текущее время для проверки; без него используется системное время.

Вспомогательные функции:

- `run_line` разбирает команду REPL и вызывает метод модели;
- `to_json` преобразует кортежи в данные, пригодные для JSON;
- `main` запускает интерактивный режим.

## Запуск

Из корня репозитория:

```bat
run.bat
```

или:

```bat
python src\main.py
```

Формат команды в REPL:

```text
имя_операции {"поле": значение, ...}
```

Команда `help` выводит список операций, `exit` и `quit` завершают работу.

## Пример работы

```text
model> create_agent {"key": 1, "timestamp": 2000000000}
model> get_agents
model> update_agent {"key": 1, "timestamp": 2000000001}

model> create_command {"key": 10, "timestamp": 2000000000, "argument": "--help", "agent": 1, "description": "пример", "tags": "demo", "processing": 0}
model> get_commands
model> update_command {"key": 10, "processing": 1}

model> create_result {"key": 100, "timestamp": 2000000000, "output": "готово", "state": "ok", "failure": "", "command": 10, "cache_hit": 1, "duration": 25}
model> get_results
model> update_result {"key": 100, "duration": 30}
model> get_recent_cache {"now": 2000000060}
[
  [
    "demo",
    1
  ]
]

model> delete_result {"key": 100}
model> delete_command {"key": 10}
model> delete_agent {"key": 1}
```

Пример обработки ошибки:

```text
model> delete_agent {"key": 999}
Ошибка: Запись с ключом 999 не найдена
```

## Тесты

```bat
python -m unittest discover -s tests -v
```

Тесты проверяют все операции модели, ограничения связей, границу
шестиминутного интервала, левое внешнее соединение и разбор команд REPL.
