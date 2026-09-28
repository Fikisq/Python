import json
import time
from typing import NamedTuple

SIX_MINUTES = 6 * 60


class Agent(NamedTuple):
    key: int
    timestamp: int


class Command(NamedTuple):
    key: int
    timestamp: int
    argument: str
    agent: int
    description: str
    tags: str
    processing: int


class Result(NamedTuple):
    key: int
    timestamp: int
    output: str
    state: str
    failure: str
    command: int
    cache_hit: int
    duration: int


class DataModel:
    def __init__(self) -> None:
        self.agents: list[Agent] = []
        self.commands: list[Command] = []
        self.results: list[Result] = []

    @staticmethod
    def _index(rows: list, key: int) -> int:
        for index, row in enumerate(rows):
            if row.key == key:
                return index
        raise KeyError(f"Запись с ключом {key} не найдена")

    @staticmethod
    def _ensure_key_is_free(rows: list, key: int) -> None:
        if any(row.key == key for row in rows):
            raise ValueError(f"Ключ {key} уже существует")

    @staticmethod
    def _update[T](rows: list[T], key: int, changes: dict) -> T:
        index = DataModel._index(rows, key)
        old_row = rows[index]
        new_row = old_row._replace(**changes)
        rows[index] = new_row
        return new_row

    def create_agent(self, key: int, timestamp: int) -> Agent:
        self._ensure_key_is_free(self.agents, key)
        agent = Agent(key, timestamp)
        self.agents.append(agent)
        return agent

    def delete_agent(self, key: int) -> Agent:
        index = self._index(self.agents, key)
        if any(command.agent == key for command in self.commands):
            raise ValueError(f"У агента {key} есть команды")
        return self.agents.pop(index)

    def get_agents(self) -> list[Agent]:
        return list(self.agents)

    def update_agent(self, key: int, **changes: int | str) -> Agent:
        return self._update(self.agents, key, changes)

    def create_command(self, **fields: int | str) -> Command:
        command = Command(**fields)
        self._ensure_key_is_free(self.commands, command.key)
        self._index(self.agents, command.agent)
        self.commands.append(command)
        return command

    def delete_command(self, key: int) -> Command:
        index = self._index(self.commands, key)
        if any(result.command == key for result in self.results):
            raise ValueError(f"У команды {key} есть результаты")
        return self.commands.pop(index)

    def get_commands(self) -> list[Command]:
        return list(self.commands)

    def update_command(self, key: int, **changes: int | str) -> Command:
        self._index(self.commands, key)
        if "agent" in changes:
            self._index(self.agents, changes["agent"])
        return self._update(self.commands, key, changes)

    def create_result(self, **fields: int | str) -> Result:
        result = Result(**fields)
        self._ensure_key_is_free(self.results, result.key)
        self._index(self.commands, result.command)
        self.results.append(result)
        return result

    def delete_result(self, key: int) -> Result:
        return self.results.pop(self._index(self.results, key))

    def get_results(self) -> list[Result]:
        return list(self.results)

    def update_result(self, key: int, **changes: int | str) -> Result:
        self._index(self.results, key)
        if "command" in changes:
            self._index(self.commands, changes["command"])
        return self._update(self.results, key, changes)

    def get_recent_cache(
            self, now: int | None = None,
    ) -> list[tuple[str, int | None]]:
        if now is None:
            current_time = int(time.time())
        else:
            current_time = now
        boundary = current_time - SIX_MINUTES
        rows: list[tuple[str, int | None]] = []

        for command in self.commands:
            if command.timestamp < boundary:
                continue
            matches = []
            for result in self.results:
                if result.command == command.key:
                    matches.append(result)
            if matches:
                for result in matches:
                    row = (command.tags, result.cache_hit)
                    rows.append(row)
            else:
                rows.append((command.tags, None))
        return rows


OPERATIONS = (
    "create_agent",
    "delete_agent",
    "get_agents",
    "update_agent",
    "create_command",
    "delete_command",
    "get_commands",
    "update_command",
    "create_result",
    "delete_result",
    "get_results",
    "update_result",
    "get_recent_cache",
)


def to_json(value: object) -> object:
    if isinstance(value, (Agent, Command, Result)):
        return value._asdict()
    if isinstance(value, (list, tuple)):
        return [to_json(item) for item in value]
    return value


def run_line(model: DataModel, line: str) -> object:
    name, _, json_text = line.partition(" ")
    if name not in OPERATIONS:
        raise ValueError(f"Неизвестная операция: {name}")

    if json_text.strip():
        arguments = json.loads(json_text)
    else:
        arguments = {}
    if not isinstance(arguments, dict):
        raise ValueError("Аргументы должны быть объектом JSON {...}")
    return getattr(model, name)(**arguments)


def main() -> None:
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
                result = to_json(run_line(model, line))
                print(json.dumps(result, ensure_ascii=False, indent=2))
            except (KeyError, ValueError, TypeError) as error:
                print("Ошибка:", error.args[0])


if __name__ == "__main__":
    main()
