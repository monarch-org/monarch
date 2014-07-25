import os
import functools
import subprocess

from click import echo
from click.testing import CliRunner

from nose.tools import with_setup
from nose.plugins.skip import SkipTest

from tests import no_op, isolated_filesystem_with_path, initialize_monarch, get_settings

try:
    import sqlalchemy
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError
    Session = sessionmaker()
except ImportError:
    sqlalchemy = None
    declarative_base = None
    sessionmaker = None
    Session = None
    text = None
    OperationalError = None


from contextlib import contextmanager

@contextmanager
def session_scope(engine):
    """Provide a transactional scope around a series of operations."""
    session = Session(bind=engine)
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


DROP_ALL_CONNECTIONS = """
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = :target_db
  AND pid <> pg_backend_pid();
"""


def requires_sqlalchemy(func):
    @functools.wraps(func)
    def wrapper(*args, **kw):
        if sqlalchemy is None:
            raise SkipTest("sqlalchemy is not installed")
        return func(*args, **kw)

    return wrapper


postgres_port = int(os.environ.get('MONARCH_POSTGRESQL_DB_PORT', 5432))


def clear_postgres_databases():
    settings = get_settings()
    for env_name in settings.ENVIRONMENTS:
        terminate_connections(env_name)
        drop_database(settings.ENVIRONMENTS[env_name])


def connection_string(environment_string):
    # like so ... 'postgresql+psycopg2://scott:tiger@localhost/mydatabase'
    settings = get_settings()
    env = settings.ENVIRONMENTS[environment_string]

    username_password_couplet = None
    if 'username' in env:
        if 'password' in env:
            username_password_couplet = "{}:{}".format(env['username'], env['password'])
        else:
            username_password_couplet = "{}".format(env['username'])

    host_string = None
    if 'port' in env:
        host_string = "{}:{}".format(env['host'], env['port'])
    else:
        host_string = env['host']

    if username_password_couplet:
        return "postgresql://{}@{}/{}".format(
            username_password_couplet,
            host_string,
            env['db_name']
        )
    else:
        return "postgresql://{}/{}".format(
            host_string,
            env['db_name']
        )


def drop_database(environment):
    """
    dropdb --port=port --host=host --username=username --password=passowrd <db_name> --if-exists
    """
    execution_array = ['dropdb', environment['db_name']]

    options = {
        '-h': environment['host'],
        '-p': str(environment['port'])
    }

    if 'username' in environment:
        options['-U'] = environment['username']

    for option in options:
        execution_array.extend([option, options[option]])

    execution_array.append('--if-exists')

    # pass PGPASSWORD as envionment variable
    kwargs = {}

    if 'password' in environment:
        env = {'PGPASSWORD': environment['password']}
        kwargs['env'] = env

    echo("Trying to execute: [{}]".format(execution_array))
    # import pdb; pdb.set_trace()
    subprocess.call(execution_array, **kwargs)


def terminate_connections(environemnt_name):

    settings = get_settings()
    env = settings.ENVIRONMENTS[environemnt_name]
    db_name = env['db_name']

    engine = get_engine(environemnt_name)
    try:
        connection = engine.connect()
        echo("DROPPING CONNECTIONS on {}".format(db_name))
        revoke = "REVOKE CONNECT ON DATABASE {} FROM public;".format(db_name)
        result = connection.execute(text(revoke))
        echo("Revoke Restults: {}".format(result))

        result = connection.execute(text(DROP_ALL_CONNECTIONS), target_db=db_name)

        for row in result:
            echo(row)

        connection.close()
    except OperationalError as e:
        echo("Could not connect to: {} -- which probably is fine".format(environemnt_name))
        # echo(e)



def get_engine(environment_string):
    return sqlalchemy.create_engine(connection_string(environment_string))


def create_db_if_necessary(environment):
    """
    createdb <db_name> --port=port --host=host --username=username --password=passowrd
    """
    execution_array = ['createdb', environment['db_name']]

    options = {
        '-h': environment['host'],
        '-p': str(environment['port'])
    }

    if 'username' in environment:
        options['-U'] = environment['username']

    for option in options:
        execution_array.extend([option, options[option]])

    # pass PGPASSWORD as envionment variable
    kwargs = {}

    if 'password' in environment:
        env = {'PGPASSWORD': environment['password']}
        kwargs['env'] = env

    echo("Trying to execute: [{}]".format(execution_array))
    subprocess.call(execution_array, **kwargs)


def populate_database(environment_string):

    engine = get_engine(environment_string)

    Base = declarative_base()

    class Puppy(Base):
        __tablename__ = 'puppies'
        id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        name = sqlalchemy.Column(sqlalchemy.String)

    # Base.metadata.create_all(engine)
    #
    # Session = sessionmaker(bind=engine)
    # session = Session()
    #
    # puppy = Puppy(name='Ralph')
    #
    # session.add(puppy)
    # session.commit()
    #
    # puppy2 = session.query(Puppy).filter_by(id=puppy.id)[0]
    #
    # assert puppy2.name == 'Ralph'
    #
    # session.close()



@requires_sqlalchemy
def test_copy_db():
    runner = CliRunner()
    with isolated_filesystem_with_path() as cwd:
        initialize_monarch(cwd, postgres_port, 'postgres')

        settings = get_settings()
        to_env = settings.ENVIRONMENTS['to_test']
        create_db_if_necessary(to_env)

        to_env = settings.ENVIRONMENTS['from_test']
        create_db_if_necessary(to_env)

        populate_database('from_test')

        clear_postgres_databases()

        # to_db = get_db(TEST_ENVIRONEMNTS['to_test'])
        # to_fishes = to_db.fishes
        #
        # assert to_fishes.count() == 0
        #
        # result = runner.invoke(cli, ['copy_db', 'from_test:to_test'], input="y\ny\n")
        # echo('trd_a output: {}'.format(result.output))
        # echo('trd_a exception: {}'.format(result.exception))
        #
        # assert to_fishes.count() == 1