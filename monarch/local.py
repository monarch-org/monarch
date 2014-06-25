import os
import shutil
import zipfile
from datetime import datetime

from .mongo import restore, dump_db
from .utils import temp_directory, exit_with_message, zipdir


def local_restore(zip_path, to_environment):
    zip = zipfile.ZipFile(zip_path)
    with temp_directory() as temp_dir:
        zip.extractall(path=temp_dir)
        restore(temp_dir, to_environment)


def local_backups(local_config):
    if 'backup_dir' not in local_config:
        exit_with_message('Local Settings not configured correctly, expecting "backup_dir"')

    backup_dir = local_config['backup_dir']

    if not os.path.isdir(backup_dir):
        exit_with_message('Directory [{}] does not exist.  Exiting ...'.format(backup_dir))

    backups = {}
    for item in os.listdir(backup_dir):
        backups[item] = os.path.join(backup_dir, item)

    return backups


def backup_localy(environment, local_settings):

    if 'backup_dir' not in local_settings:
        exit_with_message('Local Settings not configured correctly, expecting "backup_dir"')

    backup_dir = local_settings['backup_dir']

    if not os.path.isdir(backup_dir):
        exit_with_message('Directory [{}] does not exist.  Exiting ...'.format(backup_dir))

    dump_path = dump_db(environment)
    zipf = zipdir(dump_path)

    unique_file_path = generate_unique_name(backup_dir, environment)

    shutil.move(zipf.filename, unique_file_path)


def generate_unique_name(backup_dir, environemnt):
    # generate_file_name
    # database_name__2013_03_01.dmp.zip
    # or if that exists
    # database_name__2013_03_01(2).dmp.zip
    name_attempt = "{}__{}.dmp.zip".format(environemnt['db_name'], datetime.utcnow().strftime("%Y_%m_%d"))

    # check if file exists
    name_attempt_full_path = os.path.join(backup_dir, name_attempt)

    if not os.path.exists(name_attempt_full_path):
        return name_attempt_full_path
    else:
        counter = 1
        while True:
            counter += 1
            name_attempt = "{}__{}_{}.dmp.zip".format(environemnt['db_name'],
                                                      datetime.utcnow().strftime("%Y_%m_%d"), counter)
            name_attempt_full_path = os.path.join(backup_dir, name_attempt)
            if os.path.exists(name_attempt_full_path):
                continue
            else:
                return name_attempt_full_path
