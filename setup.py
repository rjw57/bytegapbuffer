from setuptools import setup, find_packages

setup(
    name="bytegapbuffer",
    description="A bytearray work-alike using a gap buffer for storage",
    version="0.1.0",
    packages=find_packages(exclude=['test']),
    install_requires=[
        'future', # py2/3 compat
    ],
)
