"""
Copyright OpenSearch Contributors
SPDX-License-Identifier: Apache-2.0
"""

import re
import ast

from setuptools import setup, find_packages

install_requirements = [
    # CVE-2026-7246: command injection in click.edit(), fixed in click 8.3.3.
    # click >= 8.2 requires Python >= 3.10, so the patched release cannot be
    # required unconditionally while this branch still supports Python 3.9.
    # Use environment markers so interpreters that can take the fix get it, and
    # older ones fall back to the newest release they can actually resolve.
    'click >= 8.3.3; python_version >= "3.10"',
    'click >= 8.1.8, < 8.2; python_version < "3.10"',
    "prompt_toolkit == 2.0.6",
    "Pygments == 2.15.1",
    "cli_helpers[styles] == 2.3.1",
    "opensearch-py == 1.0.0",
    "pyfiglet == 0.8.post1",
    "boto3 == 1.34.34",
    "requests-aws4auth == 1.2.3",
    "setuptools == 74.1.2",
]

_version_re = re.compile(r"__version__\s+=\s+(.*)")

with open("src/opensearch_sql_cli/__init__.py", "rb") as f:
    version = str(ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1)))

description = "OpenSearch SQL CLI with auto-completion and syntax highlighting"

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="opensearchsql",
    author="OpenSearch",
    author_email="opensearch-infra@amazon.com",
    version=version,
    license="Apache 2.0",
    url="https://docs-beta.opensearch.org/search-plugins/sql/cli/",
    packages=find_packages("src"),
    package_dir={"": "src"},
    package_data={"opensearch_sql_cli": ["conf/clirc", "opensearch_literals/opensearch_literals.json"]},
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=install_requirements,
    entry_points={"console_scripts": ["opensearchsql=opensearch_sql_cli.main:cli"]},
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: Unix",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: SQL",
        "Topic :: Database",
        "Topic :: Database :: Front-Ends",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.0",
)
