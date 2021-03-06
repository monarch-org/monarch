import subprocess
from tempfile import mkdtemp

import click
import pymongo
import mongoengine
from click import echo

from .utils import temp_directory
from .models import Migration, MigrationHistoryStorage
from .query_sets import querysets


def establish_datastore_connection(environment):
    mongo_db_name = environment['db_name']

    username_password_couple = ""
    if 'username' in environment:
        if 'password' in environment:
            username_password_couple = "{}:{}@".format(environment['username'], environment['password'])
        else:
            username_password_couple = "{}@".format(environment['username'])

    if 'port' in environment:
        raise Exception("port no longer supported, use the host:port syntax in the host parameter")

    host_and_port = environment['host']

    db_name = "/{}".format(environment['db_name'])

    uri = "mongodb://{username_password_couple}{host_and_port}{db_name}".format(username_password_couple=username_password_couple,
                                                                                host_and_port=host_and_port,
                                                                                db_name=db_name)

    if 'sslCAFile' in environment:
        echo('appending ssl')
        uri = "{}?ssl=true&ssl_ca_certs={}".format(uri, environment['sslCAFile'])

    echo('executing: {}'.format(uri))
    return mongoengine.connect(mongo_db_name, host=uri)


class MongoMigrationHistory(MigrationHistoryStorage, mongoengine.Document):
    """
    Mongo Table to keep track of the status of migrations
    """
    key = mongoengine.StringField()
    state = mongoengine.StringField(default=Migration.STATE_NEW)
    processed_at = mongoengine.DateTimeField()

    @classmethod
    def find_or_create_by_key(cls, migration_key):
        result = cls.objects(key=migration_key)
        if len(result) == 1:
            return result[0]
        else:
            return cls(key=migration_key).save()

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


def dump_db(from_env, **kwargs):
    """accepts temp_dir and QuerySet as keyword options"""

    if 'temp_dir' in kwargs:
        temp_dir = kwargs['temp_dir']
    else:
        temp_dir = mkdtemp()

    if 'QuerySet' in kwargs:
        QuerySet = kwargs['QuerySet']

    echo("env: {}".format(from_env))

    options = {
        '-h': from_env['host'],
        '-d': from_env['db_name'],
        '-o': temp_dir
    }
    if 'username' in from_env:
        options['-u'] = from_env['username']
    if 'password' in from_env:
        options['-p'] = from_env['password']

    if QuerySet:
        echo("In Query Set: Env: {}".format(from_env))
        connection = establish_datastore_connection(from_env)
        database = connection[from_env['db_name']]

        query_set = QuerySet(database, options)

        query_set.execute()

    else:

        execution_array = ['mongodump']
        if 'sslCAFile' in from_env:
            execution_array.append('--ssl')
            execution_array.extend(['--sslCAFile', from_env['sslCAFile']])

        for option in options:
            execution_array.extend([option, options[option]])
        echo("Executing: {}".format(execution_array))
        subprocess.call(execution_array)

    # mongorestore -h localhost --drop -d spotlight db/backups/spotlight-staging-1/
    dump_path = "{}/{}".format(temp_dir, from_env['db_name'])
    return dump_path


def copy_db(from_env, to_env, query_set=None):
    with temp_directory() as temp_dir:
        dump_path = dump_db(from_env, temp_dir=temp_dir, QuerySet=query_set)
        restore(dump_path, to_env)


def restore(dump_path, to_env):
    drop(to_env)

    options = {
        '-h': to_env['host'],
        '-d': to_env['db_name'],
    }

    if 'username' in to_env:
        options['-u'] = to_env['username']

    if 'password' in to_env:
        options['-p'] = to_env['password']

    execution_array = ['mongorestore', '--drop']

    if 'sslCAFile' in to_env:
        execution_array.append('--ssl')
        execution_array.extend(['--sslCAFile', to_env['sslCAFile']])

    for option in options:
        execution_array.extend([option, options[option]])

    execution_array.append(dump_path)

    echo("Executing: {}".format(execution_array))
    subprocess.call(execution_array)


def drop(environ):

    options = {
        '--eval': '"db.dropDatabase()"'
    }

    database_string = "{}/{}".format(environ['host'], environ['db_name'])

    execution_array = ['mongo', database_string]

    if 'sslCAFile' in environ:
        execution_array.append('--ssl')
        execution_array.extend(['--sslCAFile', environ['sslCAFile']])

    for option in options:
        execution_array.extend([option, options[option]])

    echo()
    echo("You are about to execute the following database drop")
    echo("    {}".format(' '.join(execution_array)))
    echo()
    click.confirm('ARE YOU SURE??', abort=True)

    subprocess.call(' '.join(execution_array), shell=True)
