import asyncio
from contextlib import contextmanager
import os
import shutil
import tempfile

from io import BytesIO
from unittest import mock

import pytest

from aiomanhole import StatefulCommandCompiler, InteractiveInterpreter, start_manhole


@pytest.fixture(scope="function")
def compiler():
    return StatefulCommandCompiler()


@pytest.fixture(scope="function")
def interpreter(loop):
    s = InteractiveInterpreter({}, "", loop)
    s.reader = MockStream()
    s.writer = MockStream()

    return s


@pytest.fixture(scope="function")
def loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(None)
    return loop


@contextmanager
def tcp_server(loop):
    (server,) = loop.run_until_complete(start_manhole(port=0, loop=loop))
    (socket,) = server.sockets
    (ip, port) = socket.getsockname()

    yield loop.run_until_complete(asyncio.open_connection("127.0.0.1", port))

    server.close()
    loop.run_until_complete(server.wait_closed())


@contextmanager
def unix_server(loop):
    directory = tempfile.mkdtemp()

    try:
        domain_socket = os.path.join(directory, "aiomanhole")
        (server,) = loop.run_until_complete(
            start_manhole(path=domain_socket, loop=loop)
        )

        yield loop.run_until_complete(asyncio.open_unix_connection(path=domain_socket))

        server.close()
        loop.run_until_complete(server.wait_closed())

    finally:
        shutil.rmtree(directory)


async def send_command(message, reader, writer, loop):
    # Prompt on connect
    assert await reader.read(4) == b">>> "

    # Send message
    writer.write(message)

    # Read until we see the next prompt, then strip off the prompt
    prompt = b"\n>>>"
    response = await reader.readuntil(separator=prompt)
    writer.close()
    return response[: -len(prompt)]


class MockStream:
    def __init__(self):
        self.buf = BytesIO()

    def write(self, data):
        self.buf.write(data)

    async def drain(self):
        pass

    async def readline(self):
        self.buf.seek(0)
        return self.buf.readline()


class TestStatefulCommandCompiler:
    def test_one_line(self, compiler):
        f = compiler(b"f = 5")
        assert f is not None
        ns = {}
        eval(f, ns)
        assert ns["f"] == 5

        f = compiler(b"5")
        assert f is not None
        eval(f, {})

        assert __builtins__["_"] == 5

        assert compiler(b"import asyncio") is not None

    MULTI_LINE_1 = [
        b"try:",
        b"    raise Exception",
        b"except:",
        b"    pass",
        b"",
    ]

    MULTI_LINE_2 = [
        b"for i in range(2):",
        b"    pass",
        b"",
    ]

    MULTI_LINE_3 = [
        b"while False:",
        b"    pass",
        b"",
    ]

    MULTI_LINE_4 = [
        b"class Foo:",
        b"    pass",
        b"",
    ]

    MULTI_LINE_5 = [
        b"def foo():",
        b"    pass",
        b"",
    ]

    MULTI_LINE_6 = [
        b"if False:",
        b"    pass",
        b"",
    ]

    MULTI_LINE_7 = [
        b"@decorated",
        b"def foo():",
        b"    pass",
        b"",
    ]

    @pytest.mark.parametrize(
        "input",
        [
            MULTI_LINE_1,
            MULTI_LINE_2,
            MULTI_LINE_4,
            MULTI_LINE_4,
            MULTI_LINE_5,
            MULTI_LINE_6,
            MULTI_LINE_7,
        ],
    )
    def test_multi_line(self, compiler, input):
        for line in input[:-1]:
            assert compiler(line) is None

        codeobj = compiler(input[-1])

        assert codeobj is not None

    def test_multi_line__fails_on_missing_line_ending(self, compiler):
        lines = [
            b"@decorated",
            b"def foo():",
            b"    pass",
        ]
        for line in lines[:-1]:
            assert compiler(line) is None

        codeobj = compiler(lines[-1])

        assert codeobj is None


class TestInteractiveInterpreter:
    @pytest.mark.parametrize(
        "banner,expected_result",
        [
            (b"straight up bytes", b"straight up bytes"),
            ("dat unicode tho", b"dat unicode tho"),
            (None, b""),
            (object(), ValueError),
        ],
    )
    def test_get_banner(self, banner, expected_result, interpreter):
        if isinstance(expected_result, type) and issubclass(expected_result, Exception):
            pytest.raises(expected_result, interpreter.get_banner, banner)
        else:
            assert interpreter.get_banner(banner) == expected_result

    @pytest.mark.parametrize("partial", [True, False])
    def test_write_prompt(self, interpreter, loop, partial):
        with mock.patch.object(
            interpreter.compiler, "is_partial_command", return_value=partial
        ):
            with mock.patch("sys.ps1", ">>> ", create=True), mock.patch(
                "sys.ps2", "... ", create=True
            ):
                loop.run_until_complete(interpreter.write_prompt())

        expected_value = b"... " if partial else b">>> "
        assert interpreter.writer.buf.getvalue() == expected_value

    @pytest.mark.parametrize(
        "line,partial",
        [
            (b"f = 5", False),
            (b"def foo():", True),
        ],
    )
    def test_read_command(self, interpreter, loop, line, partial):
        interpreter.reader.write(line)
        f = loop.run_until_complete(interpreter.read_command())

        if partial:
            assert f is None
        else:
            assert f is not None

    def test_read_command__raises_on_empty_read(self, interpreter, loop):
        pytest.raises(
            ConnectionResetError, loop.run_until_complete, interpreter.read_command()
        )

    @pytest.mark.parametrize(
        "value,stdout,expected_output",
        [
            (5, "", b"5\n"),
            (5, "hello", b"5\nhello"),
            (None, "hello", b"hello"),
        ],
    )
    def test_send_output(self, interpreter, loop, value, stdout, expected_output):
        loop.run_until_complete(interpreter.send_output(value, stdout))

        output = interpreter.writer.buf.getvalue()
        assert output == expected_output

    @pytest.mark.parametrize(
        "stdin,expected_output",
        [
            (b'print("hello")', b"hello"),
            (b"101", b"101"),
        ],
    )
    @pytest.mark.parametrize("server_factory", [tcp_server, unix_server])
    def test_command_over_localhost_network(
        self, loop, server_factory, stdin, expected_output
    ):
        with server_factory(loop=loop) as (reader, writer):
            output = loop.run_until_complete(
                send_command(stdin + b"\n", reader, writer, loop)
            )
            assert output == expected_output
