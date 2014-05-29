monarch
=======

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


