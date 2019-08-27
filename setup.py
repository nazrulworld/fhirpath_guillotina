#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import find_packages
from setuptools import setup


with open("README.rst") as readme_file:
    readme = readme_file.read()

with open("HISTORY.rst") as history_file:
    history = history_file.read()

requirements = [
    "Click>=6.0",
    "guillotina>=4.8.13",
    "guillotina_elasticsearch",
    "fhirpath",
]

setup_requirements = ["pytest-runner"]

test_requirements = ["pytest", "pytest-mock", "pytest-docker-fixtures"]
docs_requirements = [
    "sphinx",
    "sphinx-rtd-theme",
    "sphinxcontrib-httpdomain",
    "sphinxcontrib-httpexample",
]

setup(
    author="Md Nazrul Islam",
    author_email="email2nazrul@gmail.com",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    description="A guillotina framework powered fhirpath provider.",
    project_urls={
        "CI: Travis": "https://travis-ci.com/nazrulworld/fhirpath_guillotina",
        "Coverage: codecov": (
            "https://codecov.io/github/nazrulworld/"
            "fhirpath_guillotina"),
        "Docs: RTD": "https://fhirpath-guillotina.readthedocs.io/",
        "GitHub: issues": "https://github.com/nazrulworld/fhirpath_guillotina/issues",
        "GitHub: repo": "https://github.com/nazrulworld/fhirpath_guillotina",
    },
    entry_points={
        "console_scripts": ["fhirpath_guillotina=fhirpath_guillotina.cli:main"]
    },
    install_requires=requirements,
    license="GNU General Public License v3",
    long_description=readme + "\n\n" + history,
    include_package_data=True,
    keywords="fhirpath guillotina",
    name="fhirpath_guillotina",
    packages=find_packages(include=["fhirpath_guillotina"]),
    setup_requires=setup_requirements,
    extras_require={
        "test": test_requirements + setup_requirements,
        "docs": docs_requirements,
    },
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/nazrulworld/fhirpath_guillotina",
    version="0.1.0",
    zip_safe=False,
)
