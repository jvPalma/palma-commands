from setuptools import find_packages, setup

setup(
    name="prs",
    version="1.2.0",
    packages=find_packages(),
    install_requires=[
        # Rich library for enhanced terminal formatting and panels
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            # Maps the 'nprs' command to the main function in prs.main module
            # When installed, users can run 'nprs' from the command line
            "nprs=prs.main:main",
        ],
    },
)
