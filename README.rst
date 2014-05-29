monarch
=======

HEY WATCHOUT THIS IS IN NO WAY GURANTEED TO WORK.  HALF IMPLEMENTED FEATURES

"migrations should happen naturally"

|Build Status|

.. |Build Status| image:: https://travis-ci.org/jtushman/monarch.svg?branch=master
    :target: https://travis-ci.org/jtushman/monarch

*monarch* is a migration CLI (command line interface) to help manage developers with migrations.

What makes *monarch* unique is what it does not supply:

- *monarch* does not provide a DSL or DDL for database specific migrations (like South and alembic)
- *monarch* does not care which database you use, mongo, postres -- it does matter to us

The main usecase that was the inspiration of this tool is adding a migration to a feature using CI

[Documentation Work in Progress]

Install
-------

.. code:: bash

    pip install monarch

Usage
-----

1) Generate a Migration

.. code:: bash

    monarch create add_indexes_to_user_table

That will create a template migration that looks something like this

.. code:: python

    # in ./migrations/_201405290038_add_indexes_to_user_table_migration.py

    from monarch import MongoBackedMigration

    class AddIndexesToUserTableMigration(MongoBackedMigration):

        def run(self):
            """Write the code here that will migrate the database from one state to the next
            No Need to handle exceptions -- we will take care of that for you
            """
            raise NotImplementedError


2) Implement the Migration

Do whatever you want in that `run` method. I mean anything!  Go crazy wild man.

3) When the time is right, run the pending migrations:

.. code:: bash

    monarch migrate


Configuration
-------------

By default it will look in ./migrations/settings.py.

It should look something like this:

.. code:: python

    # migrations/settings.py
    MONGO_SETTINGS = {
        DB_NAME = 'test_monarch'
        DB_PORT = 27017
    }


