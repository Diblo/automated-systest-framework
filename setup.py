from setuptools import find_packages, setup

from src.systest.constants import VERSION

DESCRIPTION = """Automated System Test Framework (systest)
The robust system designed to automatically run behavioral system tests
to ensure the quality, functionality, and reliability of products under test.

This framework is not a single program, but a collection of tools, libraries,
and guidelines that standardize, organize, and simplify the testing process.
"""

setup(
    name="systest",
    version=VERSION,
    packages=find_packages(where="src", exclude=[
                           "__pycache__", "*.__pycache__*"]),
    package_dir={"": "src"},
    include_package_data=True,
    scripts=["src/bin/systest"],
    install_requires=[
        "behave<2.0,>=1.3.3",
        "dotenv<1.0,>=0.9.9",
        "packaging<26.0,>=25.0",
    ],
    extras_require={
        "test": [
            "pytest>=8.3,<9.0",
            "pytest-mock>=3.14,<4.0",
            "pytest-ordering>=0.6,<1.0",
            "pytest-dependency>=0.6,<1.0",
        ],
    },
    author="Henrik Ankersø",
    author_email="noreply@diblo.dk",
    url="https://github.com/Diblo/automated-systest-framework",
    description=DESCRIPTION,
    long_description=DESCRIPTION,
    license="MIT License",
    classifiers=["Programming Language :: Python :: 3.8"],
)
