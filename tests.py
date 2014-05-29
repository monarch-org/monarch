# Core
import os
import sys
import shutil
import tempfile
import functools
import contextlib
from glob import glob
from importlib import import_module

# 3rd Party
import nose
import click


from click import echo
from nose.tools import with_setup
from click.testing import CliRunner
from nose.plugins.skip import SkipTest

# Conditionals
try:
    import mongoengine
    from mongoengine.connection import _get_db as _get_db
except ImportError:
    mongoengine = None
    _get_db = None

# Local
from monarch import cli

@contextlib.contextmanager
def isolated_filesystem_with_path():
    """A context manager that creates a temporary folder and changes
    the current working directory to it for isolated filesystem tests.

    The modification here is that it adds itself to the path

    """
    cwd = os.getcwd()
    t = tempfile.mkdtemp()
    os.chdir(t)
    sys.path.insert(1, t)
    try:
        yield t
    finally:
        os.chdir(cwd)
        sys.path.remove(t)
        try:
            shutil.rmtree(t)
        except (OSError, IOError):
            pass


def requires_mongoengine(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        if mongoengine is None:
            raise SkipTest("mongoengine is not installed")
        return func(*args, **kw)

    return wrapper

def establish_mongo_connection():
    mongo_name = os.environ.get('MONARCH_MONGO_DB_NAME', 'test_monarch')
    mongo_port = int(os.environ.get('MONARCH_MONGO_DB_PORT', 27017))
    mongoengine.connect(mongo_name, port=mongo_port)
    #start clean
    clear_mongo_database()


def clear_mongo_database():
    db = _get_db()
    if db.name == os.environ.get('MONARCH_MONGO_DB_NAME', 'test_monarch'):
        db.connection.drop_database(db.name)
    else:
        echo("Can not delete a non-testing database")


def test_create_migration():
    runner = CliRunner()
    with runner.isolated_filesystem() as working_dir:
        result = runner.invoke(cli, ['generate', 'add_indexes'])
        new_files_generated = glob(working_dir + '/*/*migration.py')
        assert len(new_files_generated) == 1
        file_name = new_files_generated[0]
        assert 'add_indexes_migration.py' in file_name
        assert os.path.getsize(file_name) > 0
        assert result.exit_code == 0


def test_initialization():
    runner = CliRunner()
    with runner.isolated_filesystem() as working_dir:
        result = runner.invoke(cli, ['init'])
        settings_file = os.path.join(working_dir, 'migrations/settings.py')
        assert os.path.getsize(settings_file) > 0
        assert result.exit_code == 0


def ensure_current_migrations_module_is_loaded():
    # everytime within the same python process we add migrations we need to reload the migrations module
    # for it could be cached from a previous test
    m = import_module('migrations')
    reload(m)


def test_list_migrations():
    runner = CliRunner()

    with isolated_filesystem_with_path() as working_dir:
        for migration_name in ['add_indexes', 'add_user_table', 'add_account_table']:
            result = runner.invoke(cli, ['generate', migration_name])

        ensure_current_migrations_module_is_loaded()

        result = runner.invoke(cli, ['list'])
        assert result.exit_code == 0

TEST_MIGRATION = """
from monarch import MongoBackedMigration

class {migration_class_name}(MongoBackedMigration):

    def run(self):
        print("running a migration with no failure")
"""

TEST_FAILED_MIGRATION = """
from monarch import MongoBackedMigration

class {migration_class_name}(MongoBackedMigration):

    def run(self):
        print("running a migration with failure")
        raise Exception('Yikes we messed up the database -- oh nooooooooo')
"""

def first_migration(working_dir):
    new_files_generated = glob(working_dir + '/*/*migration.py')
    assert len(new_files_generated) == 1
    return new_files_generated[0]

@requires_mongoengine
@with_setup(establish_mongo_connection, clear_mongo_database)
def test_run_migration():
    runner = CliRunner()
    with isolated_filesystem_with_path() as cwd:
        runner.invoke(cli, ['generate', 'add_column_to_user_table'])

        # Update Migration Template with a *proper* migration
        current_migration = first_migration(cwd)
        class_name = "{}Migration".format('AddColumnToUserTable')
        with open(current_migration, 'w') as f:
            f.write(TEST_MIGRATION.format(migration_class_name=class_name))

        ensure_current_migrations_module_is_loaded()

        result = runner.invoke(cli, ['migrate'])
        # echo('output: {}'.format(result.output))
        # echo('exception: {}'.format(result.exception))
        assert result.exit_code == 0

@requires_mongoengine
@with_setup(establish_mongo_connection, clear_mongo_database)
def test_failed_migration():
    runner = CliRunner()
    with isolated_filesystem_with_path() as cwd:
        runner.invoke(cli, ['generate', 'add_account_table'])

        # Update Migration Template with a *proper* migration
        current_migration = first_migration(cwd)
        class_name = "{}Migration".format('AddAccountTable')
        with open(current_migration, 'w') as f:
            f.write(TEST_FAILED_MIGRATION.format(migration_class_name=class_name))

        ensure_current_migrations_module_is_loaded()

        result = runner.invoke(cli, ['migrate'])
        # echo('output: {}'.format(result.output))
        # echo('exception: {}'.format(result.exception))
        assert result.exit_code == -1


if __name__ == "__main__":
    nose.run()
