from setuptools import setup


setup(
    name='monarch',
    version='0.0.1',
    description='The un-migration migration tool',
    url='http://github.com/jtushman/monarch',
    author='Jonathan Tushman',
    author_email='jonathan@zefr.com',
    py_modules=['monarch'],
    install_requires=[
        'Click',
        'jinja2',
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