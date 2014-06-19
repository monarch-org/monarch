import click
import subprocess
import mongoengine
from click import echo

from .utils import temp_directory
from .models import Migration, MigrationHistoryStorage


def establish_datastore_connection(environment):
    mongo_name = environment['db_name']
    mongo_port = int(environment['port'])
    mongoengine.connect(mongo_name, port=mongo_port)


class MongoMigrationHistory(MigrationHistoryStorage, mongoengine.Document):
    """
    Mongo Table to keep track of the status of migrations
    """
    key = mongoengine.StringField()
    state = mongoengine.StringField(default=Migration.STATE_NEW)
    processed_at = mongoengine.DateTimeField()

    @classmethod
    def find_or_create_by_key(cls, migration_key):
        return cls.objects.get_or_create(key=migration_key)[0]

    @classmethod
    def find_by_key(cls, migration_key):
        results = cls.objects(key=migration_key)
        if len(results) == 1:
            return results[0]
        else:
            return None

    @classmethod
    def all(cls):
        return cls.objects()


class MongoBackedMigration(Migration):

    def update_status(self, state):
        migration_meta = MongoMigrationHistory.find_or_create_by_key(self.migration_key)
        migration_meta.update(set__state=state)

    @property
    def status(self):
        migration_meta = MongoMigrationHistory.find_or_create_by_key(self.migration_key)
        return migration_meta.state


def dump_db(from_env, temp_dir):

    echo("env: {}".format(from_env))

    options = {
        '-h': "{}:{}".format(from_env['host'], str(from_env['port'])),
        '-d': from_env['db_name'],
        '-o': temp_dir
    }
    if 'username' in from_env:
        options['-u'] = from_env['username']
    if 'password' in from_env:
        options['-p'] = from_env['password']

    execution_array = ['mongodump']
    for option in options:
        execution_array.extend([option, options[option]])
    echo("Executing: {}".format(execution_array))
    subprocess.call(execution_array)

    # mongorestore -h localhost --drop -d spotlight db/backups/spotlight-staging-1/
    dump_path = "{}/{}".format(temp_dir, from_env['db_name'])
    return dump_path


def copy_db(from_env, to_env):
    with temp_directory() as temp_dir:
        # "mongodump -h dharma.mongohq.com:10067 -d spotlight-staging-1 -u spotlight -p V4Mld1ws4C5To0N -o db/backups/"
        dump_path = dump_db(from_env, temp_dir)
        restore(dump_path, to_env)


def restore(dump_path, to_env):
    # mongorestore -h localhost --drop -d spotlight db/backups/spotlight-staging-1/

    drop(to_env)

    options = {
        '-h': "{}:{}".format(to_env['host'], str(to_env['port'])),
        '-d': to_env['db_name'],
    }

    if 'username' in to_env:
        options['-u'] = to_env['username']

    if 'password' in to_env:
        options['-p'] = to_env['password']

    execution_array = ['mongorestore', '--drop']
    for option in options:
        execution_array.extend([option, options[option]])

    execution_array.append(dump_path)

    echo("Executing: {}".format(execution_array))
    subprocess.call(execution_array)


def drop(environ):

    options = {
        '--host': environ['host'],
        '--port': str(environ['port']),
        '--eval': '"db.dropDatabase()"'
    }

    execution_array = ['mongo', environ['db_name']]
    for option in options:
        execution_array.extend([option, options[option]])

    echo()
    echo("You are about to execute the following database drop")
    echo("    {}".format(' '.join(execution_array)))
    echo()
    click.confirm('ARE YOU SURE??', abort=True)

    subprocess.call(' '.join(execution_array), shell=True)
