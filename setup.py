#!/usr/bin/env python2

from setuptools import setup

settings = {
    "name": "aiomanhole",
    "version": "0.7.0",
    "description": "Python module to provide a manhole in asyncio applications",
    "long_description": "\n\n".join(
        [open("README.rst").read(), open("CHANGELOG.rst").read()]
    ),
    "author": "Nathan Hoad",
    "author_email": "nathan@hoad.io",
    "url": "https://github.com/nathan-hoad/aiomanhole",
    "license": "BSD (3-clause)",
    "classifiers": [
        # 'Development Status :: 5 - Production/Stable',
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    "packages": ["aiomanhole"],
}

setup(**settings)
