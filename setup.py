import os
from setuptools import setup


def get_packages():
    # setuptools can't do the job :(
    packages = []
    for root, dirnames, filenames in os.walk('monarch'):
        if '__init__.py' in filenames:
            packages.append(".".join(os.path.split(root)).strip("."))

    return packages

setup(
    name='monarch',
    version='0.1.9',
    description='The un-migration migration tool',
    url='http://github.com/jtushman/monarch',
    author='Jonathan Tushman',
    author_email='jonathan@zefr.com',
    packages=get_packages(),
    install_requires=[
        'Click>2.0',
        'jinja2',
        'mongoengine',
        'boto'
    ],
    tests_require=['nose'],
    test_suite='nose.collector',
    entry_points='''
        [console_scripts]
        monarch=monarch:cli
    ''',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ],
)
