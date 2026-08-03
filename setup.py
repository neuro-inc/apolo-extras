import re

from setuptools import find_packages, setup

DIST_NAME = "apolo-extras"

with open("apolo_extras/version.py") as f:
    txt = f.read()
    try:
        version = re.findall(r'^__version__ = "([^"]+)"\r?$', txt, re.M)[0]
    except IndexError:
        raise RuntimeError("Unable to determine version.")


setup(
    name=DIST_NAME,
    version=version,
    python_requires=">=3.11.0",
    url="https://github.com/neuro-inc/neuro-extras",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
    ],
    packages=find_packages(),
    install_requires=[
        "apolo-cli>=25.8.1",
        "click>=8.4",
        "toml>=0.10.0",
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [f"{DIST_NAME}=apolo_extras:main"],
        "apolo_api": [f"{DIST_NAME}=apolo_extras:setup_plugin"],
    },
    zip_safe=False,
    include_package_data=True,
)
