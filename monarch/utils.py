import re
import shutil
from tempfile import mkdtemp
from contextlib import contextmanager

CAMEL_PAT = re.compile(r'([A-Z])')
UNDER_PAT = re.compile(r'_([a-z])')

@contextmanager
def temp_directory():
    temp_dir = mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

def camel_to_underscore(name):
    return CAMEL_PAT.sub(lambda x: '_' + x.group(1).lower(), name)


def underscore_to_camel(name):
    return UNDER_PAT.sub(lambda x: x.group(1).upper(), name.capitalize())

def sizeof_fmt(num):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0