import subprocess
from tempfile import mkdtemp

from click import echo


REQUIRED_EXECUTABLES = ('pg_dump', 'psql')


def dump_db(from_env, temp_dir=None):

    if not temp_dir:
        temp_dir = mkdtemp()

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