import os
import re
import sys
import inspect
import subprocess
from copy import copy

# 3rd Party
import click
from click import echo


class Migration(object):
    """
    All migration will inherit from this.
    """
    # States
    STATE_NEW = 'New'
    STATE_PROCESSING = 'Processing'
    STATE_FAILED = 'Failed'
    STATE_COMPLETED = 'Completed'

    @property
    def migration_key(self):
        migration_file = inspect.getfile(self.__class__)
        migration_key = os.path.splitext(os.path.basename(migration_file))[0]
        return migration_key

    @property
    def migration_name(self):
        return self.__class__.__name__

    def update_status(self, state):
        raise NotImplementedError("This is an abstract class")

    @property
    def status(self):
        raise NotImplementedError("This is an abstract class")

    def process(self, force=False):
        click.echo("Processing {}".format(self.migration_name))

        if self.status == Migration.STATE_NEW or force:
            self.update_status(Migration.STATE_PROCESSING)
            echo("Starting: {}".format(self.migration_name))
            try:
                self.run()
            except Exception:
                echo("Migration {} Failed".format(self.migration_name))
                typ, value, traceback = sys.exc_info()
                echo("Unexpected error: [{}]".format(typ))
                echo("Unexpected value: [{}]".format(value))
                echo("Unexpected traceback: [{}]".format(traceback))
                self.update_status(Migration.STATE_FAILED)
                raise
            else:
                echo("Migration {} Successful".format(self.migration_name))
                self.update_status(Migration.STATE_COMPLETED)
        elif self.status == Migration.STATE_PROCESSING:
            echo("{} is currently being processed".format(self.migration_name))
        elif self.status == Migration.STATE_COMPLETED:
            echo("{} has already been processed".format(self.migration_name))
        elif self.status == Migration.STATE_FAILED:
            echo("{} has already been processed, and failed - best to restart".format(self.migration_name))


    def run(self):
        """Should be implemented by subclass"""
        raise NotImplementedError("This is an abstract class")


class QuerySet(object):

    def __init__(self, database, mongodump_options):
        self.database = database
        self.mongodump_options = mongodump_options
        self.touched_collections = []

    @property
    def application_collection_names(self):
        """returns an array of  names of all non system tables in the database"""
        system_table_re = re.compile("system\.")

        from logging import error

        error("Database: {}".format(self.database))
        error("Connection: {}".format(self.database.connection))

        return [col_name for col_name in self.database.collection_names() if not system_table_re.match(col_name)]

    def dump_collection(self, collection_name, query=None):
        self.touched_collections.append(collection_name)
        execution_array = ['mongodump']

        collection_options = copy(self.mongodump_options)
        collection_options['-c'] = collection_name

        if query:
            collection_options['-q'] = str(query)

        for option in collection_options:
            execution_array.extend([option, collection_options[option]])
        echo("Executing: {}".format(execution_array))
        subprocess.call(execution_array)

    def run(self):
        """Should be implemented by the subclass"""
        raise NotImplementedError("This is an abstract class")

    def only(self):
        """if you want to limit the collections override this and return an array of collection names"""
        return None

    def exclude(self):
        """if you want to limit the collections override this and return an array of collection names"""
        return None

    @property
    def additional_collections(self):
        """returns the collections not specified in the query_set factoring `only` and `exclude`"""
        include_set = self.only() or self.application_collection_names
        include_set = set(include_set) - set(self.touched_collections)

        if self.exclude():
            include_set = include_set - set(self.exclude())

        return include_set

    def execute(self):
        self.run()

        for collection_name in self.additional_collections:
            self.dump_collection(collection_name)


class MigrationHistoryStorage(object):
    """Contract for persistence implementations to adhere to"""
    @classmethod
    def find_or_create_by_key(cls, migration_key):
        """Should return a MigrationHistory object"""
        raise NotImplementedError('Abstract Class')


class MigrationHistory(object):
    """Contract for persistence implementations to adhere to"""
    def __init__(self, **kwargs):
        self.key = kwargs.get('key')
        self.state = kwargs.get('state')
        self.processed_at = kwargs.get('processed_at')
