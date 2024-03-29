from setuptools import setup
from codecs import open  # To use a consistent encoding
from os import path


here = path.abspath(path.dirname(__file__))


# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# Get content from __about__.py
about = {}
with open(path.join(here, 'popget', '__about__.py'), 'r', 'utf-8') as f:
    exec(f.read(), about)


setup(
    name='popget',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=about['__version__'],

    description='Simple REST-API client for Python.',
    long_description=long_description,

    url='https://github.com/depop/popget',

    author='Depop',
    author_email='dev@depop.com',

    license='Apache 2.0',
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.11',
    ],
    install_requires=[
        'requests<3.0.0',
        'six<2.0.0',
        'enum34<2.0.0',
        'futures<4.0.0',
        'requests-futures>=0.9.7,<1.0.0',
    ],

    packages=[
        'popget',
        'popget.nonblocking',
        'popget.conf',
    ],
)
