# Core Imports
from datetime import datetime
import re
import os
import errno
import sys

# 3rd Party Imports
import click

try:
    import mongoengine
except ImportError as e:
    mongoengine = None


MIGRATION_TEMPLATE = '''
from monarch import BaseMigration

class {migration_class_name}(BaseMigration):

    def run(self):
        """Write the code here that will migrate the database from one state to the next
            No Need to handle exceptions -- we will take care of that for you
        """
        raise NotImplementedError
'''


class Config(object):

    def __init__(self):
        self.migration_directory = None

pass_config = click.make_pass_decorator(Config, ensure=True)

@click.group()
@click.option('--migration-directory', type=click.Path())
@pass_config
def cli(config, migration_directory):
    """ Your friendly migration manager
    """
    if migration_directory is None:
        migration_directory = './migrations'
    config.migration_directory = migration_directory


@cli.command()
@pass_config
def hello():
    click.echo("Hello World")

@cli.command()
@click.argument('name')
@pass_config
def generate(config, name):
    """
    Generates a migration file.  pass it a name.  execute like so:

    monarch generate [migration_name]

    i.e.

    monarch generate add_indexes_to_user_collection

    """
    create_migration_directory_if_necessary(config.migration_directory)
    migration_name = generate_migration_name(config.migration_directory, name)
    class_name = "{}Migration".format(underscore_to_camel(name))
    output = MIGRATION_TEMPLATE.format(migration_class_name=class_name)
    with open(migration_name, 'w') as f:
        f.write(output)
    click.echo("Generated Migration Template: [{}]".format(migration_name))



camel_pat = re.compile(r'([A-Z])')
under_pat = re.compile(r'_([a-z])')
def camel_to_underscore(name):
    return camel_pat.sub(lambda x: '_' + x.group(1).lower(), name)

def underscore_to_camel(name):
    return under_pat.sub(lambda x: x.group(1).upper(), name.capitalize())

def generate_migration_name(folder, name):
    # Can not start with a number so starting with a underscore
    return "{folder}/_{timestamp}_{name}_migration.py".format(
        folder=folder,
        timestamp=datetime.utcnow().strftime('%Y%m%d%H%M'),
        name=name
    )

def create_migration_directory_if_necessary(dir):
    try:
        os.makedirs(dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

# class MigrationMeta(mongoengine.Document):
#     """
#     Mongo Table to keep track of the status of migrations
#     """
#
#     key = mongoengine.StringField()
#     state = mongoengine.StringField(default='New')
#     processed_at = mongoengine.DateTimeField()
#
#     @classmethod
#     def find_or_create_by_key(cls, migration_key):
#         return cls.objects.get_or_create(key=migration_key)[0]
#
#
# class BaseMigration(object):
#     """
#     All migration will inherit from this
#     """
#
#     @property
#     def migration_key(self):
#         import inspect, os
#         migration_file = inspect.getfile(self.__class__)
#         migration_key = os.path.splitext(os.path.basename(migration_file))[0]
#         return migration_key
#
#     @property
#     def migration_name(self):
#         return self.__class__.__name__
#
#
#     def process(self):
#         print "Processing {}".format(self.migration_name)
#
#         migration_meta = MigrationMeta.find_or_create_by_key(self.migration_key)
#         if migration_meta.state == 'New':
#             migration_meta.update(set__state='Processing')
#             print "Starting: {}".format(self.migration_name)
#             try:
#                 self.run()
#             except Exception as e:
#                 print "Migration {} Failed".format(self.migration_name)
#                 typ, value, traceback = sys.exc_info()
#                 print("Unexpected error: [{}]".format(typ))
#                 print("Unexpected value: [{}]".format(value))
#                 print("Unexpected traceback: [{}]".format(traceback))
#                 migration_meta.update(set__state='Failed')
#             else:
#                 print "Migration {} Successful".format(self.migration_name)
#                 migration_meta.update(set__state='Complete')
#         elif migration_meta.state == 'Processing':
#             print "{} is currently being processed".format(self.migration_name)
#         elif migration_meta.state == 'Complete':
#             print "{} has already been processed".format(self.migration_name)
#         elif migration_meta.state == 'Failed':
#             print "{} has already been processed, and failed - best to restart".format(self.migration_name)
#
#
#
#
#
#
#     def run(self):
#         """Should be implemented by subclass"""
#         raise NotImplementedError
#
#
#

#
# @manager.command
# def test_migration():
#     """
#     This will copy either staging or production database your local database
#     Run the pending migrations
#     :return:
#     """
#     raise NotImplementedError
#
#
# @manager.command
# def migrate():
#     """
#     Runs all migrations that have yet to have run.
#     :return:
#     """
#
#     import os
#     import re
#     import inspect
#     from importlib import import_module
#     from glob import glob
#     import collections
#
#     # 1) Find all migrations in the migrations/ directory
#     # key = name, value = MigrationClass
#     migrations = {}
#     for file in glob('migrations/*_migration.py'):
#         print file
#         migration_name = os.path.splitext(os.path.basename(file))[0]
#         migration_module = import_module("migrations.{}".format(migration_name))
#
#         for name, obj in inspect.getmembers(migration_module):
#             if inspect.isclass(obj) and re.search('Migration$',name) and name != 'BaseMigration':
#                 migrations[migration_name] = obj
#
#     # 2) Ensure that the are ordered
#     ordered = collections.OrderedDict(sorted(migrations.items()))
#     for k, migration_class in ordered.iteritems():
#         migration_instance = migration_class()
#
#         # 3) Run the migration -- it will only run if it has not yet been run yet
#         migration_instance.process()
#
#

#
#
