import os
import re
import errno
import inspect
import collections
from glob import glob
from datetime import datetime
from importlib import import_module

# 3rd Party
from click import echo


def generate_migration_name(folder, name):
    # Can not start with a number so starting with a underscore
    rel_path = "{folder}/_{timestamp}_{name}_migration.py".format(
        folder=folder,
        timestamp=datetime.utcnow().strftime('%Y%m%d%H%M'),
        name=name
    )
    return os.path.abspath(rel_path)

def create_package_if_necessary(dir):
    try:
        os.makedirs(dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

    try:
        with open(os.path.join(os.path.abspath(dir), '__init__.py'), 'w') as f:
            f.write('# this file makes migrations a package\n')
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def find_migrations(config):
    migrations = {}
    for file in glob('{}/*_migration.py'.format(config.migration_directory)):
        migration_name = os.path.splitext(os.path.basename(file))[0]
        migration_module = import_module("migrations.{}".format(migration_name))
        for name, obj in inspect.getmembers(migration_module):
            if inspect.isclass(obj) and re.search('Migration$', name) and name not in ['BaseMigration',
                                                                                       'MongoBackedMigration']:
                migrations[migration_name] = obj

    # 2) Ensure that the are ordered
    ordered = collections.OrderedDict(sorted(migrations.items()))
    return ordered