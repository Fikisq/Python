import json
import socket
import time

from main import OPERATIONS


HOST = "127.0.0.1"
PORT = 5052


class RpcError(Exception):
    pass


def receive_exactly(connection: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        part = connection.recv(size - len(data))
        if not part:
            raise ConnectionError("Соединение было закрыто")
        data += part
    return data


def make_request(operation_code: int, arguments: dict) -> bytes:
    text = json.dumps(arguments, ensure_ascii=False)
    body = text.encode("utf-8")
    body_size = len(body).to_bytes(5, "little")
    code = operation_code.to_bytes(2, "little")
    return body_size + code + body


def read_response(connection: socket.socket) -> tuple[int, dict]:
    size_data = receive_exactly(connection, 3)
    body_size = int.from_bytes(size_data, "little")

    code_data = receive_exactly(connection, 1)
    operation_code = int.from_bytes(code_data, "little")

    body = receive_exactly(connection, body_size)
    response = json.loads(body.decode("utf-8"))
    if not isinstance(response, dict):
        raise ValueError("Тело ответа должно быть объектом JSON")
    return operation_code, response


class RpcClient:
    def __init__(self, host: str = HOST, port: int = PORT) -> None:
        self.host = host
        self.port = port

    def _send_request(self, operation_name: str, arguments: dict) -> object:
        operation_code = OPERATIONS.index(operation_name) + 1
        request = make_request(operation_code, arguments)

        with socket.create_connection((self.host, self.port)) as connection:
            connection.sendall(request)
            response_code, response = read_response(connection)

        if response_code != operation_code:
            raise RpcError("Код операции в ответе не совпадает с запросом")
        if not response.get("ok"):
            message = response.get("error", "Неизвестная ошибка RPC")
            raise RpcError(message)
        return response.get("result")

    def create_agent(self, key: int, timestamp: int) -> object:
        arguments = {
            "key": key,
            "timestamp": timestamp,
        }
        return self._send_request("create_agent", arguments)

    def delete_agent(self, key: int) -> object:
        return self._send_request("delete_agent", {"key": key})

    def get_agents(self) -> object:
        return self._send_request("get_agents", {})

    def update_agent(self, key: int, **changes: int | str) -> object:
        arguments = {"key": key}
        arguments.update(changes)
        return self._send_request("update_agent", arguments)

    def create_command(self, **fields: int | str) -> object:
        return self._send_request("create_command", fields)

    def delete_command(self, key: int) -> object:
        return self._send_request("delete_command", {"key": key})

    def get_commands(self) -> object:
        return self._send_request("get_commands", {})

    def update_command(self, key: int, **changes: int | str) -> object:
        arguments = {"key": key}
        arguments.update(changes)
        return self._send_request("update_command", arguments)

    def create_result(self, **fields: int | str) -> object:
        return self._send_request("create_result", fields)

    def delete_result(self, key: int) -> object:
        return self._send_request("delete_result", {"key": key})

    def get_results(self) -> object:
        return self._send_request("get_results", {})

    def update_result(self, key: int, **changes: int | str) -> object:
        arguments = {"key": key}
        arguments.update(changes)
        return self._send_request("update_result", arguments)

    def get_recent_cache(self, now: int | None = None) -> object:
        arguments = {}
        if now is not None:
            arguments["now"] = now
        return self._send_request("get_recent_cache", arguments)


def show(name: str, value: object) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2)
    print("\n" + name + ":\n" + text)


def create_and_update_data(client: RpcClient, now: int) -> None:
    agent = client.create_agent(1, now)
    show("create_agent", agent)
    show("get_agents", client.get_agents())
    show("update_agent", client.update_agent(1, timestamp=now + 1))

    command = client.create_command(
        key=10,
        timestamp=now,
        argument="--help",
        agent=1,
        description="пример команды",
        tags="demo",
        processing=0,
    )
    show("create_command", command)
    show("get_commands", client.get_commands())
    show("update_command", client.update_command(10, processing=1))

    result = client.create_result(
        key=100,
        timestamp=now,
        output="готово",
        state="ok",
        failure="",
        command=10,
        cache_hit=1,
        duration=25,
    )
    show("create_result", result)
    show("get_results", client.get_results())
    show("update_result", client.update_result(100, duration=30))
    show("get_recent_cache", client.get_recent_cache(now))


def show_error_and_delete_data(client: RpcClient) -> None:
    try:
        client.delete_agent(1)
    except RpcError as error:
        print("\nПример ошибки:\n" + str(error))

    show("delete_result", client.delete_result(100))
    show("delete_command", client.delete_command(10))
    show("delete_agent", client.delete_agent(1))


def main() -> None:
    client = RpcClient()
    now = int(time.time())
    create_and_update_data(client, now)
    show_error_and_delete_data(client)


if __name__ == "__main__":
    main()
