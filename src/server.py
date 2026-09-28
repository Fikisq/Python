import json
import socket

from main import DataModel, OPERATIONS, to_json


HOST = "127.0.0.1"
PORT = 5052

def receive_exactly(connection: socket.socket, size: int) -> bytes:
    data = b""
    while len(data) < size:
        part = connection.recv(size - len(data))
        if not part:
            raise ConnectionError("Соединение было закрыто")
        data += part
    return data


def read_request(connection: socket.socket) -> tuple[int, dict]:
    size_data = receive_exactly(connection, 5)
    body_size = int.from_bytes(size_data, "little")

    code_data = receive_exactly(connection, 2)
    operation_code = int.from_bytes(code_data, "little")

    body = receive_exactly(connection, body_size)
    arguments = json.loads(body.decode("utf-8"))
    if not isinstance(arguments, dict):
        raise ValueError("Тело запроса должно быть объектом JSON")
    return operation_code, arguments


def make_response(operation_code: int, response: dict) -> bytes:
    text = json.dumps(response, ensure_ascii=False)
    body = text.encode("utf-8")
    body_size = len(body).to_bytes(3, "little")
    code = operation_code.to_bytes(1, "little")
    return body_size + code + body


def error_text(error: Exception) -> str:
    if error.args:
        return str(error.args[0])
    return str(error)


def handle_connection(
        connection: socket.socket,
        address: tuple[str, int],
        model: DataModel,
) -> None:
    operation_code = 0
    try:
        operation_code, arguments = read_request(connection)
        if operation_code < 1 or operation_code > len(OPERATIONS):
            raise ValueError(f"Неизвестный код операции: {operation_code}")

        operation_name = OPERATIONS[operation_code - 1]
        method = getattr(model, operation_name)
        result = method(**arguments)
        response = {
            "ok": True,
            "result": to_json(result),
        }
    except Exception as error:
        response = {
            "ok": False,
            "error": error_text(error),
        }

    response_data = make_response(operation_code, response)
    connection.sendall(response_data)

    response_text = json.dumps(response, ensure_ascii=False)
    client_address = f"{address[0]}:{address[1]}"
    print(
        f"Ответ RPC: клиент={client_address}, "
        f"операция={operation_code}, тело={response_text}",
        flush=True,
    )


def serve() -> None:
    model = DataModel()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"RPC-сервер запущен на {HOST}:{PORT}", flush=True)

        while True:
            connection, address = server.accept()
            with connection:
                handle_connection(connection, address, model)


if __name__ == "__main__":
    try:
        serve()
    except KeyboardInterrupt:
        print("\nRPC-сервер остановлен")
