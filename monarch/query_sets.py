import os
import re
import inspect
from glob import glob
from importlib import import_module


def generate_queryset_name(folder, name):
    # Can not start with a number so starting with a underscore
    rel_path = "{folder}/{name}_queryset.py".format(
        folder=folder,
        name=name
    )
    return os.path.abspath(rel_path)


def querysets(config):
    query_sets = {}

    for file in glob('{}/*_queryset.py'.format(config.queryset_directory)):
        queryset_name = os.path.splitext(os.path.basename(file))[0]
        queryset_module = import_module("querysets.{}".format(queryset_name))
        for name, obj in inspect.getmembers(queryset_module):
            if inspect.isclass(obj) and re.search('QuerySet$', name) and name not in ['QuerySet']:
                query_sets[name] = obj
    return query_sets