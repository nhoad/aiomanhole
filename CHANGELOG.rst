Change History
==============

0.6.0 (30th April 2019)
 - Don't use the global loop. Thanks Timothy Fitz!
 - Allow a port of 0. Thanks Timothy Fitz!
 - Fix unit test failure.

0.5.0 (6th August 2018)
 - Fix syntax error in 3.7
 - Drop 3.4 support.

0.4.2 (3rd March 2017)
 - Handle clients putting the socket into a half-closed state when an EOF
   occurs.

0.4.1 (3rd March 2017)
 - Ensure prompts are bytes, broken in 0.4.0.

0.4.0 (3rd March 2017)
 - Ensure actual syntax errors get reported to the client.

0.3.0 (23rd August 2016)
 - **Behaviour change** aiomanhole no longer attempts to remove the UNIX socket
   on shutdown. This was flakey behaviour and does not match best practice
   (i.e. removing the UNIX socket on startup before you start your server). As
   a result, errors creating the manhole will now be logged instead of silently
   failing.
 - `start_manhole` now returns a Future that you can wait on.
 - Giving a loop to `start_manhole` now works more reliably. This won't matter
   for most people.
 - Feels "snappier"

0.2.1 (14th September 2014)
 - Handle a banner of None.
 - Fixed small typo in MANIFEST.in for the changelog.
 - Feels "snappier"

0.2.0 (25th June 2014)
 - Handle multiline statements much better.
 - setup.py pointed to wrong domain for project URL
 - Removed pointless insertion of '_' into the namespace.
 - Added lots of tests.
 - Feels "snappier"

0.1.1 (19th June 2014)
 - Use setuptools as a fallback when installing.
 - Feels "snappier"

0.1 (19th June 2014)
 - Initial release
 - Feels "snappier"
