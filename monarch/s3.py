import os
from datetime import datetime

# 3rd Party Imports
import boto
from boto.s3.key import Key
from click import echo

from .utils import temp_directory, zipdir
from .local import local_restore
from .mongo import dump_db


def get_s3_bucket(s3_settings):
    conn = boto.connect_s3(s3_settings['aws_access_key_id'], s3_settings['aws_secret_access_key'])
    bucket = conn.get_bucket(s3_settings['bucket_name'])
    return bucket


def generate_uniqueish_key(s3_settings, environment):
    bucket = get_s3_bucket(s3_settings)

    name_attempt = "{}__{}.dmp.zip".format(environment['db_name'], datetime.utcnow().strftime("%Y_%m_%d"))

    key = bucket.get_key(name_attempt)

    if not key:
        key = Key(bucket)
        key.key = name_attempt
        return key
    else:
        counter = 1
        while True:
            counter += 1
            name_attempt = "{}__{}_{}.dmp.zip".format(environment['db_name'],
                                                      datetime.utcnow().strftime("%Y_%m_%d"), counter)

            if bucket.get_key(name_attempt):
                continue
            else:
                key = Key(bucket)
                key.key = name_attempt
                return key


def backup_to_s3(environment, s3_settings):

    dump_path = dump_db(environment)
    zipf = zipdir(dump_path)

    key = generate_uniqueish_key(s3_settings, environment)

    bytes_written = key.set_contents_from_filename(zipf.filename)

    # 4) print out the name of the bucket
    echo("Wrote {} btyes to s3".format(bytes_written))


def s3_restore(key, to_enviornment):

    with temp_directory() as temp_dir:
        zip_path = os.path.join(temp_dir, 'MongoDump.zip')
        key.get_contents_to_filename(zip_path)
        local_restore(zip_path, to_enviornment)


def s3_backups(s3_config):
    """ a dict of key.name: key
    """
    bucket = get_s3_bucket(s3_config)

    buckets = {}
    for key in bucket.get_all_keys():
        buckets[key.name] = key

    return buckets
