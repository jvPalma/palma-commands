from setuptools import find_packages, setup

setup(
    name="prs",
    version="1.0.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            # Maps the 'nprs' command to the main function in prs.main module
            # When installed, users can run 'nprs' from the command line
            "nprs=prs.main:main",
        ],
    },
)
