from setuptools import setup, find_packages

setup(
    name="bytegapbuffer",
    version="0.1.1dev2",
    packages=find_packages(exclude=['test']),
    description="A bytearray work-alike using a gap buffer for storage",
    author="Rich Wareham",
    author_email="rich.bytegapbuffer@richwareham.com",
    url="https://github.com/rjw57/bytegapbuffer",
    keywords=['gap buffer', 'editor', 'collection'],
    install_requires=[
        'future', # py2/3 compat
    ],
)
