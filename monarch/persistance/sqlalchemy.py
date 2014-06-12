import sqlalchemy
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from monarch.core import Migration, MigrationHistoryStorage, MigrationHistory

Base = declarative_base()


class SqlMigrationHistory(Base, MigrationHistoryStorage):
    """
    Table to keep track of the status of migrations
    """
    __tablename__ = 'migrations'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    key = sqlalchemy.Column(sqlalchemy.String)
    state = sqlalchemy.Column(sqlalchemy.String)
    processed_at = sqlalchemy.Column(sqlalchemy.DateTime)

    @classmethod
    def find_or_create_by_key(cls, migration_key):
        migration_history = cls.objects.get_or_create(key=migration_key)[0]
        return MigrationHistory(key=migration_history.key,
                                state=migration_history.state,
                                processed_at=migration_history.processed_at)


class SqlBackedMigration(Migration):

    def update_status(self, state):
        migration_meta = SqlMigrationHistory.find_or_create_by_key(self.migration_key)
        migration_meta.state = state
        migration_meta.save()


    @property
    def status(self):
        migration_meta = SqlMigrationHistory.find_or_create_by_key(self.migration_key)
        return migration_meta.state