from setuptools import setup, find_packages

setup(
    name="promptbook",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "PySide6>=6.0.0"
    ],
    entry_points={
        'console_scripts': [
            'promptbook=promptbook.main:main',
        ],
    },
) 