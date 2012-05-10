# -*- coding: utf8 -*-

import pymongo

from envvars import MONGO_URI, DB_NAME


def get_db():
  connection = pymongo.Connection(MONGO_URI)
  return connection[DB_NAME]


def log(s):
  print s.encode('utf8')  # heroku can't log unicode


def quotify(s):
  """reddit markdown quotes a string"""
  return u'> {}'.format(s.replace('\n', '\n> '))