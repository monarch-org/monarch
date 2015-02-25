.. -*-restructuredtext-*-

monarch
=======

|Build Status|

.. |Build Status| image:: https://travis-ci.org/monarch-org/monarch.svg?branch=master
    :target: https://travis-ci.org/monarch-org/monarch.svg?branch=master


The Concept
-----------

"migrations should happen naturally"

**monarch** is a mongo utility belt that helps developers and admins deal with common admin use-cases.  The main use-case
that this library was built for was _migrations_ but it does a bunch or other useful things like makes it easy to
backup, restore, and copy environments between one another.

It has been very helpful for our teams -- and hopefully you guys can find it useful as well.


The Interface
-------------

Migrations
~~~~~~~~~~
Simple Migration Framework

``generate <migration_name>``
    Generates a new migration template.  In this template you write the necessary code to perform your migration

``list_migrations <env_name>``
    Lists all of the migrations and there current status

``migrate <env_name>``
    Runs all pending migration on the given environment.  Normally you will use `copy_db` to move the production environment
    locally and test the migrations locally first before doing on production

``migrate_one <migration_name> <env_name>``
    Run a specific migration -- no matter its status.  Helpful for rapid test iteration


Environment Management
~~~~~~~~~~~~~~~~~~~~~~
Utilities for moving databases between environments.  With support for backup/restore locally and to s3

``init``
    Initializes monarch for your project

``list_environments``
    Lists the environments under management

``backup <env name>``
    Backs ups a given database.  You can backup to your local file system or to a Amazon S3 bucket
    Make sure you have BACKUPS configured in your migrations/settings.py file
    It will dump your database and compress it and give it a unique name

``restore  <backup_name>:<env_name>``
    Restore a backup into the provided environment.  It will truncate the database before the import

``list_backups``
    Lists the available backups

``copy_db <from_env>:<to_env>``
    Copies one database into another database

    It will make an archive of the "From" database and then truncate the "To" database and restore that archive into the
    "To" database

    This is most useful for copying the production database locally to test migrations before doing it for reals


Partial Copies and Backups
~~~~~~~~~~~~~~~~~~~~~~~~~
As your database grows, it is often useful to copy only a subset of your data.  For this we introduce the concept
of a QuerySet.  You can use these to define the subset of data you would like to bring over.

``generate_query_set``
   Generates a new query_set template.  In this template you write the necessary code to perform your query_set

``list_query_sets``
   Lists the available QuerySets


A queryset can look like:

.. code:: python

    from monarch import QuerySet
    from click import echo
    
    class AwesomeDogsQuerySet(QuerySet):
    
        def run(self):
    
            awesome_dogs = self.database.dogs.find({"type": "Awesome"})
            awesome_dog_ids = [dog['_id'] for dog in awesome_dogs]
            echo("awesome dog ids: {}".format(awesome_dog_ids))
    
            self.dump_collection('dogs', {"_id": {"$in": awesome_dog_ids}})
            self.dump_collection('dog_houses', {"dog_id": {"$in": awesome_dog_ids}})


You can also use click's prompt function to make it dynamic, and prompt the use for input. Like so

.. code:: python

    from monarch import QuerySet
    from click import echo, prompt
    
    class AccountQuerySet(QuerySet):
    
        def run(self):
    
            account_id = prompt('Please enter a account id', type=int)
    
            account_i_care_about = self.database.accounts.find({"_id": account_id})
    
            self.dump_collection('account', {"_id": account_id})
            self.dump_collection('campaigns', {"account_id": account_i_care_about})


Then to use them you can pass them into `copy_db` and `backup` with the --query-set options like so:

.. code:: bash

    copy_db production:development -q AccountQuerySet



The Installation
----------------

.. code:: bash

    pip install monarch


You need to configure **monarch** for each project.  Simply run ``monarch init`` in the root of your project.  Then
go into `migrations.settings.py` to configure your environments and backups


Migrations
----------

One of the core design principals behind **monarch** is that it does not provide a DSL or DDL for database
specific migrations (like South and alembic)

You write your migrations in pure python using whatever libraries you like.


When we develop a feature we implement the following:

- the **feature**
- the **tests**
- and the necessary **migrations** that move the production data to where it needs to be to rock the new feature

So now with **monarch** we can implement a Pull Request(PR) with the feature, test and migration.
And once your Continuous Integration says that your tests are cool then you can deploy and run
the pending migrations needed for your feature.


Example Use Case
----------------

1) **Generate a Migration**

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


2) **Implement the Migration**

Do whatever you want in that `run` method. I mean anything!  Go crazy wild man.

3) **Test the Migration**

.. code:: bash

    # copy the production db locally
    monarch copy_db production:development

    # check the status of the pending migrations
    monarch list_migrations development

    # try running the migrations
    monarch migrate development

    # everything cool?

    # just to be sure -- lets make a backup
    monarch backup production

    # time to rock
    monarch migrate production

    # not cool?
    # fix your migration and try again
    monarch copy_db production:development

    # and so on ....


RoadMap
-------
* Support for PostgreSQL and the like
* Use only pymongo (not mongoengine)
