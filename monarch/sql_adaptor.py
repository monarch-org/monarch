from tempfile import mkdtemp

from click import echo
from sqlalchemy import create_engine


from .utils import temp_directory


class SqlAdaptor(object):

    def __init__(self, environment):
        self.environment = environment
        self.connection_string = environment['connection_string']
        self.engine = create_engine(self.connection_string)

    @property
    def connection(self):
        return self.engine.connect()

    @classmethod
    def dump_db(cls, from_env, temp_dir=None):

        if not temp_dir:
            temp_dir = mkdtemp()



