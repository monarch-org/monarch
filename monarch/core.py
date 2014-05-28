import os
import sys
import inspect

import click

try:
    import mongoengine
except ImportError as e:
    mongoengine = None

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
            click.echo("Starting: {}".format(self.migration_name))
            try:
                self.run()
            except Exception:
                click.echo("Migration {} Failed".format(self.migration_name))
                typ, value, traceback = sys.exc_info()
                click.echo("Unexpected error: [{}]".format(typ))
                click.echo("Unexpected value: [{}]".format(value))
                click.echo("Unexpected traceback: [{}]".format(traceback))
                self.update_status(Migration.STATE_FAILED)
                raise
            else:
                click.echo("Migration {} Successful".format(self.migration_name))
                self.update_status(Migration.STATE_COMPLETED)
        elif self.status == Migration.STATE_PROCESSING:
            click.echo("{} is currently being processed".format(self.migration_name))
        elif self.status == Migration.STATE_COMPLETED:
            click.echo("{} has already been processed".format(self.migration_name))
        elif self.status == Migration.STATE_FAILED:
            click.echo("{} has already been processed, and failed - best to restart".format(self.migration_name))

    def run(self):
        """Should be implemented by subclass"""
        raise NotImplementedError


class MigrationMeta(mongoengine.Document):
    """
    Mongo Table to keep track of the status of migrations
    """
    key = mongoengine.StringField()
    state = mongoengine.StringField(default=Migration.STATE_NEW)
    processed_at = mongoengine.DateTimeField()

    @classmethod
    def find_or_create_by_key(cls, migration_key):
        return cls.objects.get_or_create(key=migration_key)[0]


class MongoBackedMigration(Migration):

    def update_status(self, state):
        migration_meta = MigrationMeta.find_or_create_by_key(self.migration_key)
        migration_meta.update(set__state=state)

    @property
    def status(self):
        migration_meta = MigrationMeta.find_or_create_by_key(self.migration_key)
        return migration_meta.state
