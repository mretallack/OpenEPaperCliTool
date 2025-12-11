#!/usr/bin/env python3
"""Setup script for eink-cli tool."""

from setuptools import setup, find_packages

try:
    with open("../README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = "CLI tool for sending content to eink displays over BLE"

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="eink-cli",
    version="1.0.0",
    author="EInk CLI Tool Contributors",
    author_email="",
    description="CLI tool for sending content to eink displays over BLE",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/OpenEPaperLink/eink-cli",
    license="Apache-2.0",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: System :: Hardware",
        "Topic :: Communications",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "eink-cli=eink_cli.cli:main",
        ],
    },
)