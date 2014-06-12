import os
import sys
import inspect

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

    def process(self):
        click.echo("Processing {}".format(self.migration_name))

        if self.status == Migration.STATE_NEW:
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
        raise NotImplementedError


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
