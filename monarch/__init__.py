# Core Imports
import os
import re
import sys
from importlib import import_module

# 3rd Party Imports
import click

from click import echo, progressbar

#exposing echo and progressbar as utilities for migrations
echo = echo
progressbar = progressbar

# Local Imports
from .models import Migration, QuerySet
from .local import local_restore, local_backups, backup_localy
from .s3 import get_s3_bucket, generate_uniqueish_key, backup_to_s3, s3_restore, s3_backups
from .migrations import generate_migration_name, create_package_if_necessary, find_migrations
from .query_sets import querysets, generate_queryset_name

from .mongo import MongoMigrationHistory, MongoBackedMigration, \
    establish_datastore_connection, \
    restore as restore_mongo_db, \
    copy_db as copy_mongo_db, \
    drop as drop_mongo_db

from .utils import temp_directory, camel_to_underscore, \
    underscore_to_camel, sizeof_fmt, exit_with_message

from .templates import MIGRATION_TEMPLATE, CONFIG_TEMPLATE, QUERYSET_TEMPLATE


class Config(object):

    def __init__(self):
        self.migration_directory = './migrations'
        self.queryset_directory = './querysets'
        self.config_directory = None

    def configure_from_settings_file(self):
        try:
            sys.path.append(os.getcwd())

            settings = import_module('migrations.settings')
        except ImportError:
            exit_with_message("Could not find your settings.py file -- did you run monarch init?")

        if not hasattr(settings, 'ENVIRONMENTS'):
            exit_with_message('Configuration file should have a ENVIRONMENTS method set')
        else:
            self.environments = settings.ENVIRONMENTS

        if hasattr(settings, 'BACKUPS'):
            self.backups = settings.BACKUPS

            if 'S3' in self.backups and 'LOCAL' in self.backups:
                exit_with_message('BACKUPS Setting has both LOCAL and S3 config -- choose one')
            elif 'S3' not in self.backups and 'LOCAL' not in self.backups:
                exit_with_message('BACKUPS are configured, but S3 or LOCAL is not defined -- please define one')
            elif 'S3' in self.backups:
                s3_config = self.backups['S3']

                required_config = ['bucket_name', 'aws_access_key_id', 'aws_secret_access_key']

                missing_config = []

                for item in required_config:
                    if item not in s3_config:
                        missing_config.append(item)

                if missing_config:
                    msg = "Missing [] items in S3 section of your settings.py".format(", ".join(missing_config))
                    exit_with_message(msg)

pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group()
@pass_config
@click.pass_context
def cli(ctx, config):
    """ Your friendly migration manager

        To get help on a specific function you may append --help to the function
        i.e.
        monarch generate --help
    """
    if ctx.invoked_subcommand != 'init':
        config.configure_from_settings_file()


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
    create_package_if_necessary(config.migration_directory)
    migration_name = generate_migration_name(config.migration_directory, name)
    class_name = "{}Migration".format(underscore_to_camel(name))
    output = MIGRATION_TEMPLATE.format(migration_class_name=class_name, base_class='MongoBackedMigration')
    with open(migration_name, 'w') as f:
        f.write(output)
    click.echo("Generated Migration Template: [{}]".format(migration_name))

@cli.command()
@click.argument('name')
@pass_config
def generate_query_set(config, name):
    """
    Generates a query_set file.  pass it a name.  execute like so:

    monarch generate_query_set [queryset_name]

    i.e.

    monarch generate_query_set data_for_account

    """
    create_package_if_necessary(config.queryset_directory)
    queryset_name = generate_queryset_name(config.queryset_directory, name)
    class_name = "{}QuerySet".format(underscore_to_camel(name))
    output = QUERYSET_TEMPLATE.format(queryset_class_name=class_name, base_class='QuerySet')
    with open(queryset_name, 'w') as f:
        f.write(output)
    click.echo("Generated Query Set: [{}]".format(queryset_name))



@cli.command(name='list_migrations')
@click.argument('environment')
@pass_config
def lizt(config, environment):
    """ Lists the migrations and the status against the specified environemnt

    """
    if environment not in config.environments:
        exit_with_message("Environment not described in settings.py")

    migrations_on_file_system = find_migrations(config)

    establish_datastore_connection(config.environments[environment])

    if migrations_on_file_system:
        click.echo("Here are the migrations:")
        echo("{:50} {}".format('MIGRATIONS', 'STATUS'))
        for migration_name in migrations_on_file_system:
            migration_meta = MongoMigrationHistory.find_by_key(migration_name)
            if migration_meta:
                echo("{:50} {}".format(migration_name, migration_meta.state))
            else:
                echo("{:50} NOT RUN".format(migration_name))

    else:
        click.echo("No pending migrations")


@cli.command()
@click.argument('environment')
@pass_config
def migrate(config, environment):
    """
    Runs all migrations that have yet to have run.
    :return:
    """
    if environment not in config.environments:
        exit_with_message("Environment not described in settings.py")

    check_for_hazardous_operations(config, environment)

    # 1) Find all migrations in the migrations/ directory
    # key = name, value = MigrationClass
    migrations = find_migrations(config)
    if migrations:
        establish_datastore_connection(config.environments[environment])
        for k, migration_class in migrations.iteritems():
            migration_instance = migration_class()

            # 3) Run the migration -- it will only run if it has not yet been run yet
            migration_instance.process()
    else:
        click.echo("No migrations exist")



@cli.command()
@click.argument('migration_name')
@click.argument('environment')
@pass_config
def migrate_one(config, migration_name, environment):
    """
    Runs all migrations that have yet to have run.
    :return:
    """
    if environment not in config.environments:
        exit_with_message("Environment not described in settings.py")

    check_for_hazardous_operations(config, environment)

    establish_datastore_connection(config.environments[environment])

    # 1) Find all migrations in the migrations/ directory
    # key = name, value = MigrationClass
    migration = find_migration(config, migration_name)
    migration.process(force=True)


def find_migration(config, migration_name):

    migrations = find_migrations(config)
    migration_class = migrations[migration_name]
    return migration_class()



@cli.command()
@click.option('--migration-directory', default='./migrations', help='path to where you want to store your migrations')
def init(migration_directory):
    """ Generates a default setting file.

        It will it in ./migrations and will create the package if it does not exist

    """

    create_package_if_necessary(migration_directory)
    settings_file = os.path.join(os.path.abspath(migration_directory), 'settings.py')

    if os.path.exists(settings_file):
        click.confirm("A settings file already exists.  Are you sure you want to overwrite it?", abort=True)

    with open(settings_file, 'w') as f:
        f.write(CONFIG_TEMPLATE)

    msg = """We just created a shinny new configuration file for you.  You can find it here:

    {}

    You are encouraged to open it up and modify it for your needs
    """.format(settings_file)

    echo(msg)


@cli.command()
@click.option('--query-set', help='provide optional query-set filter, default is the entire db')
@click.argument('from_to')
@pass_config
def copy_db(config, from_to, query_set):
    """ Copys a database and imports into another database

        Example

        monarch import_db production:local
        monarch import_db staging:local

    """
    if ':' not in from_to:
        exit_with_message("Expecting from:to syntax like production:local")

    from_db, to_db = from_to.split(':')

    check_for_hazardous_operations(config, to_db)

    if config.environments is None:
        exit_with_message('Configuration file should have a ENVIRONMENTS set')

    if from_db not in config.environments:
        exit_with_message('Environments does not have a specification for {}'.format(from_db))

    if to_db not in config.environments:
        exit_with_message('Environments does not have a specification for {}'.format(to_db))

    query_set_class = None
    if query_set:
        if query_set not in querysets(config):
            exit_with_message('Could not find specified query_set in your queryset folder')
        else:
            query_set_class = querysets(config)[query_set]

    if click.confirm('Are you SURE you want to copy data from {} into {}?'.format(from_db, to_db)):
        echo()
        echo("Okay, you asked for it ...")
        echo()
        copy_mongo_db(config.environments[from_db],
                      config.environments[to_db],
                      query_set_class)


@cli.command()
@click.argument('environment')
@pass_config
def drop_db(config, environment):
    """ drops the database -- ARE YOU SURE YOU WANT TO DO THIS
    """

    check_for_hazardous_operations(config, environment)

    drop_mongo_db(config.environments[environment])


@cli.command()
@click.argument('environment')
@click.option('--name', help='name to prefix the backup with')
@click.option('--query-set', help='provide optional query-set filter, default is the entire db')
@pass_config
def backup(config, environment, name, query_set):
    """ Backs up a given datastore
        It is configured in the BACKUPS section of settings
        You can back up locally or to S3

        use --name if you want to specify a name, otherwise it will use your environment name

    """
    env_name = environment

    if not hasattr(config, 'backups'):
        exit_with_message('BACKUPS not configured, exiting')

    environment = confirm_environment(config, env_name)

    query_set_class = None
    if query_set:
        if query_set not in querysets(config):
            exit_with_message('Could not find specified query_set in your queryset folder')
        else:
            query_set_class = querysets(config)[query_set]

    if 'LOCAL' in config.backups:
        backup_localy(environment, config.backups['LOCAL'], name, query_set_class)
    elif 'S3' in config.backups:
        backup_to_s3(environment, config.backups['S3'], name, query_set_class)
    else:
        exit_with_message('BACKUPS not configured, exiting')


@cli.command()
@pass_config
def list_backups(config):
    """ Lists available backups
    """
    if config.backups is None:
        exit_with_message('BACKUPS not configured, exiting')

    if 'LOCAL' in config.backups:
        list_local_backups(config.backups['LOCAL'])
    elif 'S3' in config.backups:
        list_s3_backups(config.backups['S3'])
    else:
        exit_with_message('BACKUPS not configured, exiting')


@cli.command()
@pass_config
def list_environments(config):
    """ Lists Configured Environments
    """
    if config.environments:
        for env in config.environments:
            echo("{:40}: {}".format(env, config.environments[env]))
    else:
        echo()
        echo("Yikes you have no environments set up -- you should set some up.  Maybe rerun monarch init")
        echo()


@cli.command()
@pass_config
def list_query_sets(config):
    """ Lists Query Sets
    """
    query_sets_on_file_system = querysets(config)

    if query_sets_on_file_system:
        click.echo("Here are the query sets:")
        echo('QUERY SETS')
        for queryset_name in query_sets_on_file_system:
            echo(queryset_name)

    else:
        click.echo("No query sets created")


@cli.command()
@click.argument('from_to')
@pass_config
def restore(config, from_to):
    """ Restores a backup into a destination database.  Provide a dump name that you can get from

        monarch list_backups

        Example

        monarch restore adid-development__2014_06_18.dmp.zip:development

    """
    if ':' not in from_to:
        exit_with_message("Expecting from:to syntax like production:local")

    backup, to_db = from_to.split(':')

    check_for_hazardous_operations(config, to_db)

    if config.environments is None:
        exit_with_message('Configuration file should have a ENVIRONMENTS set')

    if to_db not in config.environments:
        exit_with_message('Environments does not have a specification for {}'.format(to_db))

    if backup not in backups(config):
        exit_with_message('Can not find backup {}, run monarch list_backups to see your options'.format(backup))

    msg = 'Are you SURE you want to restore backup into into {}? It will delete the database first'.format(to_db)
    if click.confirm(msg):
        echo()
        echo("Okay, you asked for it ...")
        echo()
        restore_db(config, backups(config)[backup], config.environments[to_db])


def confirm_environment(config, env_name):
    if env_name not in config.environments:
        exit_with_message("{} is not in settings.  Exiting ...".format(env_name))
    else:
        return config.environments[env_name]


def list_local_backups(local_config):

    _local_backups = local_backups(local_config)
    if _local_backups:
        for backup in _local_backups:
            echo("{:50} {}".format(backup, sizeof_fmt(os.path.getsize(_local_backups[backup]))))
    else:
        echo()
        echo('You have not backups yet -- make some?  monarch backup <env_name>')
        echo()


def list_s3_backups(s3_settings):
    _s3_backups = s3_backups(s3_settings)
    if _s3_backups:
        for backup in _s3_backups:
            echo("{:50} {}".format(backup, sizeof_fmt(_s3_backups[backup].size)))
    else:
        echo()
        echo('You have not backups yet -- make some?  monarch backup <env_name>')
        echo()


def restore_db(config, path_or_key, to_environment):
    """unzips the file then runs a restore"""

    if config.backups is None:
        exit_with_message('BACKUPS not configured, exiting')

    if 'LOCAL' in config.backups:
        return local_restore(path_or_key, to_environment)
    elif 'S3' in config.backups:
        return s3_restore(path_or_key, to_environment)
    else:
        exit_with_message('BACKUPS not configured, exiting')

    echo()
    echo("Rock and roll that seemed to go well -- Nice work")
    echo()


def backups(config):
    """returns a dictionary of {backup_name: backup_path}"""
    if config.backups is None:
        exit_with_message('BACKUPS not configured, exiting')

    if 'LOCAL' in config.backups:
        return local_backups(config.backups['LOCAL'])
    elif 'S3' in config.backups:
        return s3_backups(config.backups['S3'])
    else:
        exit_with_message('BACKUPS not configured, exiting')


def test_for_human():
    from random import randint
    int_1 = randint(0, 100)
    int_2 = randint(0, 100)

    sum = int_1 + int_2

    value = click.prompt('What is the sum of {} and {}?'.format(int_1, int_2), type=int)

    if value != sum:
        exit_with_message('You have chosen poorly')
    else:
        echo("Good enough for me -- continue")

ensure_smarter_than_a_4_year_old = test_for_human


def check_for_hazardous_operations(config, env_name):

    if env_name not in config.environments:
        exit_with_message("Environment not described in settings.py")

    env = config.environments[env_name]
    db_name = env['db_name']
    db_host = env['host']

    ends_with_dot_local = re.compile("local$")

    def looks_like_a_remote_host(host_name):
        if db_host in ('localhost', '127.0.0.1'):
            return False

        if ends_with_dot_local.search(db_host) is not None:
            return False

        #not sure so assuming remote
        return True

    dangerous = (env_name == 'production' or looks_like_a_remote_host(db_host))

    if dangerous:
        echo('You are about to perform a potentially hazardous operation. \n\nenv: [{}] db_host [{}]\nComputer Breath-o-lizer test:'.format(env_name, db_host))
        ensure_smarter_than_a_4_year_old()
