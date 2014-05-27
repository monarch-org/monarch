from setuptools import setup


setup(
    name='monarch',
    version='0.0.1',
    py_modules=['monarch'],
    install_requires=[
        'Click',
        'jinja2',
    ],
    entry_points='''
        [console_scripts]
        monarch=monarch:cli
    ''',
)