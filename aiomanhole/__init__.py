import asyncio
import contextlib
import functools
import sys
import traceback

from codeop import CommandCompiler
from io import BytesIO, StringIO


__all__ = ['start_manhole']


class StatefulCommandCompiler(CommandCompiler):
    """A command compiler that buffers input until a full command is available."""

    def __init__(self):
        super().__init__()
        self.buf = BytesIO()

    def is_partial_command(self):
        return bool(self.buf.getvalue())

    def __call__(self, source, **kwargs):
        buf = self.buf
        if self.is_partial_command():
            buf.write(b'\n')
        buf.write(source)

        code = self.buf.getvalue().decode('utf8')

        codeobj = super().__call__(code, **kwargs)

        if codeobj:
            self.reset()
        return codeobj

    def reset(self):
        self.buf.seek(0)
        self.buf.truncate(0)


class InteractiveInterpreter:
    """An interactive asynchronous interpreter."""

    def __init__(self, namespace, banner, loop):
        self.namespace = namespace
        self.banner = self.get_banner(banner)
        self.compiler = StatefulCommandCompiler()
        self.loop = loop

    def get_banner(self, banner):
        if isinstance(banner, bytes):
            return banner
        elif isinstance(banner, str):
            return banner.encode('utf8')
        elif banner is None:
            return b''
        else:
            raise ValueError("Cannot handle unknown banner type {!}, expected str or bytes".format(banner.__class__.__name__))

    def attempt_compile(self, line):
        return self.compiler(line)

    @asyncio.coroutine
    def send_exception(self):
        """When an exception has occurred, write the traceback to the user."""
        self.compiler.reset()

        exc = traceback.format_exc()
        self.writer.write(exc.encode('utf8'))

        yield from self.writer.drain()

    @asyncio.coroutine
    def attempt_exec(self, codeobj, namespace):
        with contextlib.redirect_stdout(StringIO()) as buf:
            value = yield from self._real_exec(codeobj, namespace)

        return value, buf.getvalue()

    @asyncio.coroutine
    def _real_exec(self, codeobj, namespace):
        yield  # quick hack to pretend to be a coroutine, which attempt_exec expects
        return eval(codeobj, namespace)

    @asyncio.coroutine
    def handle_one_command(self):
        """Process a single command. May have many lines."""

        while True:
            yield from self.write_prompt()
            codeobj = yield from self.read_command()

            if codeobj is not None:
                yield from self.run_command(codeobj)

    @asyncio.coroutine
    def run_command(self, codeobj):
        """Execute a compiled code object, and write the output back to the client."""
        try:
            value, stdout = yield from self.attempt_exec(codeobj, self.namespace)
        except Exception:
            yield from self.send_exception()
            return
        else:
            yield from self.send_output(value, stdout)

    @asyncio.coroutine
    def write_prompt(self):
        writer = self.writer

        if self.compiler.is_partial_command():
            writer.write(sys.ps2.encode('utf8'))
        else:
            writer.write(sys.ps1.encode('utf8'))

        yield from writer.drain()

    @asyncio.coroutine
    def read_command(self):
        """Read a command from the user line by line.

        Returns a code object suitable for execution.
        """

        reader = self.reader

        line = yield from reader.readline()
        if line == b'':  # lost connection
            raise ConnectionResetError()

        try:
            # skip the newline to make CommandCompiler work as advertised
            codeobj = self.attempt_compile(line.rstrip(b'\n'))
        except SyntaxError:
            yield from self.send_exception()
            return

        return codeobj

    @asyncio.coroutine
    def send_output(self, value, stdout):
        """Write the output or value of the expression back to user.

        >>> 5
        5
        >>> print('cash rules everything around me')
        cash rules everything around me
        """

        writer = self.writer

        if value is not None:
            writer.write('{!r}\n'.format(value).encode('utf8'))

        if stdout:
            writer.write(stdout.encode('utf8'))

        yield from writer.drain()

    def _setup_prompts(self):
        try:
            sys.ps1
        except AttributeError:
            sys.ps1 = ">>> "
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = "... "

    @asyncio.coroutine
    def __call__(self, reader, writer):
        """Main entry point for an interpreter session with a single client."""

        self.reader = reader
        self.writer = writer

        self._setup_prompts()

        if self.banner:
            writer.write(self.banner)
            yield from writer.drain()

        while True:
            try:
                yield from self.handle_one_command()
            except ConnectionResetError:
                writer.close()
                break
            except Exception as e:
                traceback.print_exc()


class ThreadedInteractiveInterpreter(InteractiveInterpreter):
    """An interactive asynchronous interpreter that executes
    statements/expressions in a thread.

    This is useful for aiding to protect against accidentally running
    slow/terminal code in your main loop, which would destroy the process.

    Also accepts a timeout, which defaults to five seconds. This won't kill
    the running statement (good luck killing a thread) but it will at least
    yield control back to the manhole.
    """
    def __init__(self, *args, command_timeout=5, **kwargs):
        super().__init__(*args, **kwargs)
        self.command_timeout = command_timeout

    @asyncio.coroutine
    def _real_exec(self, codeobj, namespace):
        task = self.loop.run_in_executor(None, eval, codeobj, namespace)
        if self.command_timeout:
            task = asyncio.wait_for(task, self.command_timeout, loop=self.loop)
        value = yield from task
        return value


class InterpreterFactory:
    """Factory class for creating interpreters."""

    def __init__(self, interpreter_class, *args, namespace=None, shared=False, loop=None, **kwargs):
        self.interpreter_class = interpreter_class
        self.namespace = namespace or {}
        self.shared = shared
        self.args = args
        self.kwargs = kwargs
        self.loop = loop or asyncio.get_event_loop()

    def __call__(self, reader, writer):
        interpreter = self.interpreter_class(
            *self.args,
            loop=self.loop,
            namespace=self.namespace if self.shared else dict(self.namespace),
            **self.kwargs
        )
        return asyncio.ensure_future(interpreter(reader, writer), loop=self.loop)


def start_manhole(banner=None, host='127.0.0.1', port=None, path=None,
        namespace=None, loop=None, threaded=False, command_timeout=5,
        shared=False):

    """Starts a manhole server on a given TCP and/or UNIX address.

    Keyword arguments:
        banner - Text to display when client initially connects.
        host - interface to bind on.
        port - port to listen on over TCP. Default is disabled.
        path - filesystem path to listen on over UNIX sockets. Deafult is disabled.
        namespace - dictionary namespace to provide to connected clients.
        threaded - if True, use a threaded interpreter. False, run them in the
                   middle of the event loop. See ThreadedInteractiveInterpreter
                   for details.
        command_timeout - timeout in seconds for commands. Only applies if
                          `threaded` is True.
        shared - If True, share a single namespace between all clients.

    Returns a Future for starting the server(s).
    """

    loop = loop or asyncio.get_event_loop()

    if (port, path) == (None, None):
        raise ValueError('At least one of port or path must be given')

    if threaded:
        interpreter_class = functools.partial(
            ThreadedInteractiveInterpreter, command_timeout=command_timeout)
    else:
        interpreter_class = InteractiveInterpreter

    client_cb = InterpreterFactory(
        interpreter_class, shared=shared, namespace=namespace, banner=banner,
        loop=loop)

    coros = []

    if path:
        f = asyncio.ensure_future(
            asyncio.start_unix_server(client_cb, path=path, loop=loop), loop=loop)
        coros.append(f)

    if port is not None:
        f = asyncio.ensure_future(asyncio.start_server(
            client_cb, host=host, port=port, loop=loop), loop=loop)
        coros.append(f)

    return asyncio.gather(*coros, loop=loop)


if __name__ == '__main__':
    start_manhole(path='/var/tmp/testing.manhole', banner='Well this is neat\n', threaded=True, shared=True)
    asyncio.get_event_loop().run_forever()
