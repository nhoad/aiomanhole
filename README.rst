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
