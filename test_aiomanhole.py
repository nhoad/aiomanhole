import asyncio

from io import BytesIO
from unittest import mock

import pytest

from aiomanhole import StatefulCommandCompiler, InteractiveInterpreter


@pytest.fixture(scope='function')
def compiler():
    return StatefulCommandCompiler()


@pytest.fixture(scope='function')
def interpreter(loop):
    s = InteractiveInterpreter({}, '', loop)
    s.reader = MockStream()
    s.writer = MockStream()

    return s


@pytest.fixture(scope='function')
def loop():
    return asyncio.get_event_loop()


class MockStream:
    def __init__(self):
        self.buf = BytesIO()

    def write(self, data):
        self.buf.write(data)

    @asyncio.coroutine
    def drain(self):
        yield
        pass

    @asyncio.coroutine
    def readline(self):
        yield
        self.buf.seek(0)
        return self.buf.readline()


class TestStatefulCommandCompiler:
    def test_one_line(self, compiler):
        f = compiler(b'f = 5')
        assert f is not None
        ns = {}
        eval(f, ns)
        assert ns['f'] == 5

        f = compiler(b'5')
        assert f is not None
        eval(f, {})

        assert __builtins__['_'] == 5

        assert compiler(b'import asyncio') is not None

    MULTI_LINE_1 = [
        b'try:',
        b'    raise Exception',
        b'except:',
        b'    pass',
        b'',
    ]

    MULTI_LINE_2 = [
        b'for i in range(2):',
        b'    pass',
        b'',
    ]

    MULTI_LINE_3 = [
        b'while False:',
        b'    pass',
        b'',
    ]

    MULTI_LINE_4 = [
        b'class Foo:',
        b'    pass',
        b'',
    ]

    MULTI_LINE_5 = [
        b'def foo():',
        b'    pass',
        b'',
    ]

    MULTI_LINE_6 = [
        b'if False:',
        b'    pass',
        b'',
    ]

    MULTI_LINE_7 = [
        b'@decorated',
        b'def foo():',
        b'    pass',
        b'',
    ]

    @pytest.mark.parametrize('input', [
        MULTI_LINE_1,
        MULTI_LINE_2,
        MULTI_LINE_4,
        MULTI_LINE_4,
        MULTI_LINE_5,
        MULTI_LINE_6,
        MULTI_LINE_7,
    ])
    def test_multi_line(self, compiler, input):
        for line in input[:-1]:
            assert compiler(line) is None

        codeobj = compiler(input[-1])

        assert codeobj is not None

    def test_multi_line__fails_on_missing_line_ending(self, compiler):
        lines = [
            b'@decorated',
            b'def foo():',
            b'    pass',
        ]
        for line in lines[:-1]:
            assert compiler(line) is None

        codeobj = compiler(lines[-1])

        assert codeobj is None


class TestInteractiveInterpreter:
    @pytest.mark.parametrize('partial', [True, False])
    def test_write_prompt(self, interpreter, loop, partial):
        with mock.patch.object(interpreter.compiler, 'is_partial_command', return_value=partial):
            loop.run_until_complete(interpreter.write_prompt())

        expected_value = b'... ' if partial else b'>>> '
        assert interpreter.writer.buf.getvalue() == expected_value

    @pytest.mark.parametrize('line,partial', [
        (b'f = 5', False),
        (b'def foo():', True),
    ])
    def test_read_command(self, interpreter, loop, line, partial):
        interpreter.reader.write(line)
        f = loop.run_until_complete(interpreter.read_command())

        if partial:
            assert f is None
        else:
            assert f is not None

    def test_read_command__raises_on_empty_read(self, interpreter, loop):
        pytest.raises(ConnectionResetError, loop.run_until_complete, interpreter.read_command())

    @pytest.mark.parametrize('value,stdout,expected_output', [
        (5, '', b'5\n'),
        (5, 'hello', b'5\nhello'),
        (None, 'hello', b'hello'),
    ])
    def test_send_output(self, interpreter, loop, value, stdout, expected_output):
        loop.run_until_complete(interpreter.send_output(value, stdout))

        output = interpreter.writer.buf.getvalue()
        assert output == expected_output
