from setuptools import find_packages, setup

setup(
    name="prs",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "rich>=14.0.0",
        "textual>=0.60.0",
    ],
    entry_points={
        "console_scripts": [
            # "nprs=prs.main:main",
            "nprs=prs.main:main",
        ],
    },
)
