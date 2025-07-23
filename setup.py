"""
Setup script for OpenSearch SQL CLI
"""

import re
import ast
from setuptools import setup, find_packages

install_requirements = [
    # SQL CLI
    "markdown-it-py==3.0.0",
    "mdurl==0.1.2",
    "prompt_toolkit==3.0.51",
    "Pygments==2.19.2",
    "PyYAML==6.0.2",
    "rich==14.0.0",
    "shellingham==1.5.4",
    "typer==0.16.0",
    "typing_extensions==4.14.1",
    # Java Gateway Python
    "py4j==0.10.9.9",
]

_version_re = re.compile(r"__version__\s+=\s+(.*)")

with open("src/main/python/opensearchsql_cli/__init__.py", "rb") as f:
    version = str(
        ast.literal_eval(_version_re.search(f.read().decode("utf-8")).group(1))
    )


description = "OpenSearch SQL CLI with SQL Plug-in Version Selection"

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="opensearchsql",
    author="OpenSearch",
    author_email="opensearch-infra@amazon.com",
    version=version,
    license="Apache 2.0",
    url="https://docs-beta.opensearch.org/search-plugins/sql/cli/",
    package_dir={"": "src/main/python"},
    packages=find_packages(where="src/main/python"),
    include_package_data=True,
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=install_requirements,
    entry_points={"console_scripts": ["opensearchsql=opensearchsql_cli.main:main"]},
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: Unix",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: SQL",
        "Topic :: Database",
        "Topic :: Database :: Front-Ends",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
)
