#!/usr/bin/env python2

import os
import sys

try:
    from distutils.core import setup
except ImportError:
    from setuptools import setup

# Publish Helper.
if sys.argv[-1] == 'publish':
    os.system('python3 setup.py sdist upload')
    sys.exit()

settings = {
    'name': 'aiomanhole',
    'version': '0.2.0',
    'description': "Python module to provide a manhole in asyncio applications",
    'long_description': open('README.rst').read(),
    'author': 'Nathan Hoad',
    'author_email': 'nathan@getoffmalawn.com',
    'url': 'https://github.com/nathan-hoad/aiomanhole',
    'license': 'BSD (3-clause)',
    'classifiers': [
        # 'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    'packages': ['aiomanhole']
}

setup(**settings)
