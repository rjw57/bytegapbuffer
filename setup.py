from setuptools import setup, find_packages

setup(
    name="bytegapbuffer",
    version="0.1.1",
    packages=find_packages(exclude=['test']),
    install_requires=[
        'future', # py2/3 compat
    ],
)
