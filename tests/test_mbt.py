import sys
import threading
import time
from pathlib import Path

from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, rule


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from client import RpcClient, RpcError  # noqa: E402
from main import DataModel, to_json  # noqa: E402
from server import serve  # noqa: E402


KEYS = st.integers(min_value=0, max_value=4)
NUMBERS = st.integers(min_value=0, max_value=1000)
FLAGS = st.integers(min_value=0, max_value=1)
TEXT = st.text(alphabet="abcXYZ", min_size=0, max_size=6)
NOWS = st.one_of(st.none(), NUMBERS)

COMMAND_FIELDS = st.fixed_dictionaries({
    "key": KEYS,
    "timestamp": NUMBERS,
    "argument": TEXT,
    "agent": KEYS,
    "description": TEXT,
    "tags": TEXT,
    "processing": FLAGS,
})

RESULT_FIELDS = st.fixed_dictionaries({
    "key": KEYS,
    "timestamp": NUMBERS,
    "output": TEXT,
    "state": TEXT,
    "failure": TEXT,
    "command": KEYS,
    "cache_hit": FLAGS,
    "duration": NUMBERS,
})

COMMAND_CHANGES = st.one_of(
    st.fixed_dictionaries({"processing": FLAGS}),
    st.fixed_dictionaries({"agent": KEYS}),
)

RESULT_CHANGES = st.one_of(
    st.fixed_dictionaries({"duration": NUMBERS}),
    st.fixed_dictionaries({"command": KEYS}),
)


server_thread = None
server_error = None


def run_server() -> None:
    global server_error
    try:
        serve(False)
    except BaseException as error:
        server_error = error


def start_server() -> None:
    global server_thread
    if server_thread is not None:
        return
    server_thread = threading.Thread(
        target=run_server,
        daemon=True,
    )
    server_thread.start()

    client = RpcClient()
    for _ in range(100):
        try:
            client.get_agents()
            return
        except OSError:
            time.sleep(0.01)
    raise RuntimeError("RPC-сервер не запустился")


@settings(max_examples=30, stateful_step_count=30, deadline=None)
class RpcStateMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        start_server()
        if server_error is not None:
            raise RuntimeError(f"RPC-сервер остановился: {server_error!r}")
        self.client = RpcClient()
        self.model = DataModel()
        self._clear_server()

    def _clear_server(self) -> None:
        for result in self.client.get_results():
            self.client.delete_result(result["key"])
        for command in self.client.get_commands():
            self.client.delete_command(command["key"])
        for agent in self.client.get_agents():
            self.client.delete_agent(agent["key"])

    def _compare(self, operation: str, arguments: dict) -> None:
        model_method = getattr(self.model, operation)
        client_method = getattr(self.client, operation)

        try:
            expected = model_method(**arguments)
        except (KeyError, ValueError, TypeError) as error:
            message = str(error.args[0])
            try:
                client_method(**arguments)
            except RpcError as rpc_error:
                assert str(rpc_error) == message
            else:
                raise AssertionError("RPC не вернул ожидаемую ошибку")
            return

        actual = client_method(**arguments)
        assert actual == to_json(expected)

    @rule(key=KEYS, timestamp=NUMBERS)
    def create_agent(self, key: int, timestamp: int) -> None:
        self._compare("create_agent", {"key": key, "timestamp": timestamp})

    @rule(key=KEYS)
    def delete_agent(self, key: int) -> None:
        self._compare("delete_agent", {"key": key})

    @rule()
    def get_agents(self) -> None:
        self._compare("get_agents", {})

    @rule(key=KEYS, timestamp=NUMBERS)
    def update_agent(self, key: int, timestamp: int) -> None:
        self._compare("update_agent", {"key": key, "timestamp": timestamp})

    @rule(fields=COMMAND_FIELDS)
    def create_command(self, fields: dict) -> None:
        self._compare("create_command", fields)

    @rule(key=KEYS)
    def delete_command(self, key: int) -> None:
        self._compare("delete_command", {"key": key})

    @rule()
    def get_commands(self) -> None:
        self._compare("get_commands", {})

    @rule(key=KEYS, changes=COMMAND_CHANGES)
    def update_command(self, key: int, changes: dict) -> None:
        arguments = {"key": key}
        arguments.update(changes)
        self._compare("update_command", arguments)

    @rule(fields=RESULT_FIELDS)
    def create_result(self, fields: dict) -> None:
        self._compare("create_result", fields)

    @rule(key=KEYS)
    def delete_result(self, key: int) -> None:
        self._compare("delete_result", {"key": key})

    @rule()
    def get_results(self) -> None:
        self._compare("get_results", {})

    @rule(key=KEYS, changes=RESULT_CHANGES)
    def update_result(self, key: int, changes: dict) -> None:
        arguments = {"key": key}
        arguments.update(changes)
        self._compare("update_result", arguments)

    @rule(now=NOWS)
    def get_recent_cache(self, now: int | None) -> None:
        arguments = {}
        if now is not None:
            arguments["now"] = now
        self._compare("get_recent_cache", arguments)


class TestRpcStateMachine(RpcStateMachine.TestCase):
    pass
