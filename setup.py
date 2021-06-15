from setuptools import setup, find_packages
from io import open
from os import path

from tree_config import __version__

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

URL = 'https://github.com/matham/tree-config'

setup(
    name='tree-config',
    version=__version__,
    author='Matthew Einhorn',
    author_email='matt@einhorn.dev',
    license='MIT',
    description=(
        'Automatic app configuration of app objects.'),
    long_description=long_description,
    url=URL,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
    ],
    packages=find_packages(),
    project_urls={
        'Bug Reports': URL + '/issues',
        'Source': URL,
    },
)
