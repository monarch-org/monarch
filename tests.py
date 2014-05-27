import os
from glob import glob

import nose
import click
from click.testing import CliRunner

from monarch import cli

def test_create_migration():
    runner = CliRunner()
    with runner.isolated_filesystem() as working_dir:
        result = runner.invoke(cli, ['generate', 'add_indexes'])
        click.echo(result.output)
        new_files_generated = glob(working_dir + '/*/*')
        assert len(new_files_generated) == 1
        file_name = new_files_generated[0]
        assert 'add_indexes_migration.py' in file_name
        assert os.path.getsize(file_name) > 0
        assert result.exit_code == 0






if __name__ == "__main__":
    nose.run()
