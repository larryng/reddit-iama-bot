#!/usr/bin/python

import os
import sys
import time
import narwal
import pymongo
import urlparse


USERNAME = os.environ['REDDIT_USERNAME']
PASSWORD = os.environ['REDDIT_PASSWORD']

QA_FORMAT = (
  u'**[Question]({qlink}?context=1) ({asker}):**\n\n'
  u'{question}\n\n'
  u'**[Answer]({alink}?context=1) ({host}):**\n\n'
  u'{answer}\n\n'
  u'*****\n'
)
TOP_FORMAT = (
  u'**Top-level Comment:**\n\n'
  u'{answer}\n'
)
HEADER_FORMAT = (
  u'Answers from [{host}](/user/{host}/) (last updated: {last_updated}):\n\n'
  u'*****\n'
)
SECOND_HEADER_FORMAT = (
  u'(page {})\n\n'
  u'*****\n'
)
TIME_FORMAT = "%b %d, %Y @ %I:%M:%S %P EST"
BASE_URL = u'http://www.reddit.com/'
BOT_NAME = u'narwal_bot'


def quotify(s):
  return u'> {}'.format(s.replace('\n', '\n> '))


def get_qa(first_comments, author):
  def helper(comments, parent=None):
    lst = []
    for comment in comments:
      if not isinstance(comment, narwal.things.Comment):
        continue
      if comment.author == author:
        if not parent or parent.author != BOT_NAME:
          lst.append((parent, comment))
      if comment.replies:
        lst += helper(comment.replies, comment)
    return lst
  lst = helper(first_comments)
  return sorted(lst, key=lambda (p, c): c.created)


def format_qa(lst, host, limit=10000):
  rlst = []
  slst = [HEADER_FORMAT.format(last_updated=time.strftime(TIME_FORMAT, time.localtime()),
                               host=host)]
  charcount = 0
  page = 1
  for q, a in lst:
    if q:
      s = QA_FORMAT.format(qlink=q.permalink,
                           alink=a.permalink,
                           asker=q.author if q.author else u'[deleted]',
                           question=quotify(q.body if q.body else u'[deleted]'),
                           host=host,
                           answer=quotify(a.body))
    else:
      s = TOP_FORMAT.format(answer=quotify(a.body))
    charcount += len(s) + 1
    if charcount >= limit:
      rlst.append('\n'.join(slst))
      page += 1
      header = SECOND_HEADER_FORMAT.format(page) 
      slst = [header,
              s]
      charcount = len(s) + len(header)
    else:
      slst.append(s)
  if slst:
    rlst.append('\n'.join(slst))
  return rlst


def compile(api, path):
  listblob = api.get(path)
  link = listblob[0][0]
  comments = listblob[1]
  qa = get_qa(comments, link.author)
  sqa = format_qa(qa, link.author)
  return link.author, sqa


def main():
  if len(sys.argv) == 2:
    api = narwal.connect(USERNAME, PASSWORD, user_agent='narwal_bot iama bot')
    path = sys.argv[1]
    if path.startswith(BASE_URL):
      path = path[len(BASE_URL):]
    host, sqa = compile(api, path)
    for i, s in enumerate(sqa):
      with open('{}{}.txt'.format(host, i), 'w') as f:
        f.write(s)
  else:
    print 'wrong args'


if __name__ == "__main__":
  main()