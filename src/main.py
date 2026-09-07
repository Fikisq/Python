"""Практическая работа №1, вариант 13, этап 1.

Модель слоя доступа к данным. Данные живут только в памяти,
на диск ничего не пишется.

Три таблицы (ER-диаграмма, рис. 13):
    Agent   -- агент, который отправляет команды;
    Command -- команда агента;
    Result  -- результат выполнения команды.

Связи:
    Command.agent  -> Agent.key
    Result.command -> Command.key

Строка таблицы -- это кортеж. Используется NamedTuple: тот же
кортеж, но у элементов есть имена, поэтому можно писать
command.tags вместо command[5]. Кортеж менять нельзя, поэтому
при редактировании старый кортеж заменяется новым.

Все поля таблиц -- это либо int, либо str, поэтому новые значения
полей в методах update_* имеют тип int | str.

Ошибки:
    KeyError   -- запись с таким ключом не найдена;
    ValueError -- нарушено правило (ключ занят, есть связанные
                  записи, попытка сменить key);
    TypeError  -- переданы не те поля.
"""

import json
import time
from typing import NamedTuple

SIX_MINUTES = 6 * 60


class Agent(NamedTuple):
    """Строка таблицы Agent.

    key: 1 -- номер агента, уникален
    timestamp: 2000000000 -- время создания, секунды Unix
    """

    key: int
    timestamp: int


class Command(NamedTuple):
    """Строка таблицы Command.

    key: 10 -- номер команды, уникален
    timestamp: 2000000000 -- время создания, секунды Unix
    argument: "--help" -- аргумент команды
    agent: 1 -- номер агента-отправителя (Agent.key)
    description: "вывести справку" -- описание
    tags: "demo" -- теги
    processing: 0 -- обработана ли: 0 нет, 1 да
    """

    key: int
    timestamp: int
    argument: str
    agent: int
    description: str
    tags: str
    processing: int


class Result(NamedTuple):
    """Строка таблицы Result.

    key: 100 -- номер результата, уникален
    timestamp: 2000000000 -- время получения, секунды Unix
    output: "готово" -- вывод команды
    state: "ok" -- состояние: ok, error и т.п.
    failure: "" -- текст ошибки, если была
    command: 10 -- номер команды (Command.key)
    cache_hit: 1 -- из кэша ли результат: 0 нет, 1 да
    duration: 25 -- время выполнения, секунды
    """

    key: int
    timestamp: int
    output: str
    state: str
    failure: str
    command: int
    cache_hit: int
    duration: int


class DataModel:
    """Хранит три таблицы вместе и выполняет операции над ними.

    Класс нужен для удобства: три списка лежат в одном объекте,
    и их не надо передавать в каждую функцию отдельно.

    agents: [Agent(key=1, timestamp=2000000000)] -- таблица Agent
    commands: [Command(key=10, ...)] -- таблица Command
    results: [Result(key=100, ...)] -- таблица Result
    """

    def __init__(self) -> None:
        """Создать три пустые таблицы."""
        self.agents: list[Agent] = []
        self.commands: list[Command] = []
        self.results: list[Result] = []

    @staticmethod
    def _find(rows: list, key: int) -> int:
        """Найти строку по ключу, иначе KeyError.

        rows: [Agent(key=1, ...), Agent(key=2, ...)] -- таблица
        key: 2 -- искомый ключ
        return index: 1 -- позиция строки в списке
        """
        for index, row in enumerate(rows):
            if row.key == key:
                return index
        raise KeyError(f"Запись с ключом {key} не найдена")

    @staticmethod
    def _check_free(rows: list, key: int) -> None:
        """Проверить, что ключ не занят, иначе ValueError.

        rows: [Agent(key=1, ...)] -- таблица
        key: 1 -- проверяемый ключ
        return None
        """
        for row in rows:
            if row.key == key:
                raise ValueError(f"Ключ {key} уже существует")

    @staticmethod
    def _update(rows: list, key: int, changes: dict) -> tuple:
        """Заменить строку с ключом key копией с изменёнными полями.

        rows: [Agent(key=1, timestamp=5)] -- таблица
        key: 1 -- ключ изменяемой строки
        changes: {"timestamp": 7} -- новые значения полей
        return row: Agent(key=1, timestamp=7) -- обновлённая строка
        """
        if "key" in changes:
            raise ValueError("Поле key изменять нельзя")
        index = DataModel._find(rows, key)
        rows[index] = rows[index]._replace(**changes)
        return rows[index]

    def create_agent(self, key: int, timestamp: int) -> Agent:
        """Добавить агента.

        key: 1 -- номер агента
        timestamp: 2000000000 -- время создания
        return agent: Agent(key=1, timestamp=2000000000)
        """
        self._check_free(self.agents, key)
        agent = Agent(key, timestamp)
        self.agents.append(agent)
        return agent

    def delete_agent(self, key: int) -> Agent:
        """Удалить агента. Нельзя, если у него есть команды.

        key: 1 -- номер агента
        return agent: Agent(key=1, timestamp=2000000000) -- удалённый
        """
        for command in self.commands:
            if command.agent == key:
                raise ValueError(f"У агента {key} есть команды")
        return self.agents.pop(self._find(self.agents, key))

    def get_agents(self) -> list[Agent]:
        """Получить всех агентов.

        return agents: [Agent(key=1, timestamp=2000000000), ...]
        """
        return list(self.agents)

    def update_agent(self, key: int, **changes: int | str) -> Agent:
        """Изменить поля агента.

        key: 1 -- номер агента
        changes: {"timestamp": 2000000001} -- новые значения полей
        return agent: Agent(key=1, timestamp=2000000001)
        """
        return self._update(self.agents, key, changes)

    def create_command(self, **fields: int | str) -> Command:
        """Добавить команду. Агент fields["agent"] должен существовать.

        fields: {"key": 10, "timestamp": 2000000000,
                 "argument": "--help", "agent": 1,
                 "description": "справка", "tags": "demo",
                 "processing": 0} -- все 7 полей Command
        return command: Command(key=10, ..., processing=0)
        """
        command = Command(**fields)
        self._check_free(self.commands, command.key)
        self._find(self.agents, command.agent)
        self.commands.append(command)
        return command

    def delete_command(self, key: int) -> Command:
        """Удалить команду. Нельзя, если у неё есть результаты.

        key: 10 -- номер команды
        return command: Command(key=10, ...) -- удалённая
        """
        for result in self.results:
            if result.command == key:
                raise ValueError(f"У команды {key} есть результаты")
        return self.commands.pop(self._find(self.commands, key))

    def get_commands(self) -> list[Command]:
        """Получить все команды.

        return commands: [Command(key=10, ...), Command(key=11, ...)]
        """
        return list(self.commands)

    def update_command(self, key: int, **changes: int | str) -> Command:
        """Изменить поля команды. Новый agent должен существовать.

        key: 10 -- номер команды
        changes: {"processing": 1} -- новые значения полей
        return command: Command(key=10, ..., processing=1)
        """
        if "agent" in changes:
            self._find(self.agents, changes["agent"])
        return self._update(self.commands, key, changes)

    def create_result(self, **fields: int | str) -> Result:
        """Добавить результат. Команда fields["command"] должна быть.

        fields: {"key": 100, "timestamp": 2000000000,
                 "output": "готово", "state": "ok", "failure": "",
                 "command": 10, "cache_hit": 1,
                 "duration": 25} -- все 8 полей Result
        return result: Result(key=100, ..., duration=25)
        """
        result = Result(**fields)
        self._check_free(self.results, result.key)
        self._find(self.commands, result.command)
        self.results.append(result)
        return result

    def delete_result(self, key: int) -> Result:
        """Удалить результат.

        key: 100 -- номер результата
        return result: Result(key=100, ...) -- удалённый
        """
        return self.results.pop(self._find(self.results, key))

    def get_results(self) -> list[Result]:
        """Получить все результаты.

        return results: [Result(key=100, ...), ...]
        """
        return list(self.results)

    def update_result(self, key: int, **changes: int | str) -> Result:
        """Изменить поля результата. Новая command должна существовать.

        key: 100 -- номер результата
        changes: {"duration": 30} -- новые значения полей
        return result: Result(key=100, ..., duration=30)
        """
        if "command" in changes:
            self._find(self.commands, changes["command"])
        return self._update(self.results, key, changes)

    def get_recent_cache(
        self, now: int | None = None,
    ) -> list[tuple[str, int | None]]:
        """Выборка по формуле задания (пункт 3).

        Формула: π tags, cache_hit ( σ timestamp >= now-6min (C)
                 ⟕ C.key = R.command  R )

        1. σ  -- берём команды не старше 6 минут от now.
        2. ⟕  -- к каждой команде подставляем её результаты
                 (result.command == command.key). Если результатов
                 нет, команда остаётся, а вместо cache_hit -- None.
        3. π  -- из пары оставляем только tags и cache_hit.

        now: 2000000060 -- текущее время в секундах;
                           None -- взять системное время
        return rows: [("demo", 1), ("none", None)] -- пары
                     (tags, cache_hit)
        """
        if now is None:
            now = int(time.time())
        rows: list[tuple[str, int | None]] = []
        for command in self.commands:
            if command.timestamp < now - SIX_MINUTES:
                continue
            found = False
            for result in self.results:
                if result.command == command.key:
                    rows.append((command.tags, result.cache_hit))
                    found = True
            if not found:
                rows.append((command.tags, None))
        return rows


OPERATIONS = (
    "create_agent", "delete_agent", "get_agents", "update_agent",
    "create_command", "delete_command", "get_commands",
    "update_command",
    "create_result", "delete_result", "get_results", "update_result",
    "get_recent_cache",
)


def to_json(value: object) -> object:
    """Подготовить ответ модели к печати в JSON.

    value: Agent(key=1, timestamp=5) -- строка таблицы,
           список строк или список кортежей
    return data: {"key": 1, "timestamp": 5} -- словарь или список
    """
    if isinstance(value, (Agent, Command, Result)):
        return value._asdict()
    if isinstance(value, (list, tuple)):
        return [to_json(item) for item in value]
    return value


def run_line(model: DataModel, line: str) -> object:
    """Разобрать строку из REPL и вызвать метод модели.

    model: DataModel() -- модель с таблицами
    line: 'create_agent {"key": 1, "timestamp": 5}' -- ввод
    return result: Agent(key=1, timestamp=5) -- ответ метода
    """
    name, _, json_text = line.partition(" ")
    if name not in OPERATIONS:
        raise ValueError(f"Неизвестная операция: {name}")
    arguments = json.loads(json_text) if json_text.strip() else {}
    if not isinstance(arguments, dict):
        raise ValueError("Аргументы должны быть объектом JSON {...}")
    return getattr(model, name)(**arguments)


def main() -> None:
    """Интерактивный режим (REPL). Работает до слова exit или Ctrl+Z."""
    model = DataModel()
    print("Формат: имя_операции {\"поле\": значение}. help - справка.")
    while True:
        try:
            line = input("model> ").strip()
        except EOFError:
            break
        if line in ("exit", "quit"):
            break
        if line == "help":
            print("\n".join(OPERATIONS))
        elif line:
            try:
                answer = to_json(run_line(model, line))
                print(json.dumps(answer, ensure_ascii=False, indent=2))
            except (KeyError, ValueError, TypeError) as error:
                print("Ошибка:", error.args[0])


if __name__ == "__main__":
    main()
