# -*- coding: utf8 -*-

import narwal
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


def all_comments(clisting):
  while clisting.has_more:
    clisting.children = clisting[:-1] + list(clisting.more())
  for c in clisting.children:
    if c.replies:
      all_comments(c.replies)


def deep_count(comments):
  count = 0
  for c in comments:
    if isinstance(c, narwal.things.Comment):
      count += 1
      if c.replies:
        count += deep_count(c.replies)
  return count