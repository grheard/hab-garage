#!/usr/bin/python3

from setuptools import setup


setup(
    name="garage",
    version="0",
    description="garage hab controller",
    author="grheard",
    author_email="grheard@gmail.com",
    python_requires=">=3.6",
    packages=["garage"],
    entry_points={
        "console_scripts": ["garage = garage.garage:main"]
    },
    install_requires=['pigpio','paho-mqtt','w1thermsensor']
)
