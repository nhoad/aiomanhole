aiomanhole
==========

Manhole for accessing asyncio applications. This is useful for debugging
application state in situations where you have access to the process, but need
to access internal application state.

Adding a manhole to your application is simple::

    from aiomanhole import start_manhole

    start_manhole(namespace={
        'gizmo': application_state_gizmo,
        'whatsit': application_state_whatsit,
    })

Quick example, in one shell, run this::

    $ python -m aiomanhole

In a secondary shell, run this::

    $ nc -U /var/tmp/testing.manhole
    Well this is neat
    >>> f = 5 + 5
    >>> f
    10
    >>> import os
    >>> os.getpid()
    4238
    >>> import sys
    >>> sys.exit(0)


And you'll see the manhole you started has exited.

The package provides both a threaded and non-threaded interpreter, and allows
you to share the namespace between clients if you want.


I'm getting "Address is already in use" when I start! Help!
===========================================================

Unlike regular TCP/UDP sockets, UNIX domain sockets are entries in the
filesystem. When your process shuts down, the UNIX socket that is created is
not cleaned up. What this means is that when your application starts up again,
it will attempt to bind a UNIX socket to that path again and fail, as it is
already present (it's "already in use").

The standard approach to working with UNIX sockets is to delete them before you
try to bind to it again, for example::

    import os
    try:
        os.unlink('/path/to/my.manhole')
    except FileNotFoundError:
        pass
    start_manhole('/path/to/my.manhole')


You may be tempted to try and clean up the socket on shutdown, but don't. What
if your application crashes? What if your computer loses power? There are lots
of things that can go wrong, and hoping the previous run was successful, while
admirably positive, is not something you can do.


Can I specify what is available in the manhole?
===============================================
Yes! When you call `start_manhole`, just pass along a dictionary of what you
want to provide as the namespace parameter::

    from aiomanhole import start_manhole

    start_manhole(namespace={
        'gizmo': application_state_gizmo,
        'whatsit': application_state_whatsit,
        'None': 5,  # don't do this though
    })


When should I use threaded=True?
================================

Specifying threaded=True means that statements in the interactive session are
executed in a thread, as opposed to executing them in the event loop.

Say for example you did this in a non-threaded interactive session::

    >>> while True:
    ...  pass
    ...

You've just broken your application! You can't abort that without restarting
the application. If however you ran that in a threaded application, you'd
'only' have a thread trashing the CPU, slowing down your application, as
opposed to making it totally unresponsive.

By default, a threaded interpreter will time out commands after 5 seconds,
though this is configurable. Not that this will **not** kill the thread, but
allow you to keep running commands.
