#!/usr/bin/python
# -*- coding: utf8 -*- 

import os
import sys
import time
import narwal
import pymongo
import urlparse


USERNAME = os.environ['REDDIT_USERNAME']
PASSWORD = os.environ['REDDIT_PASSWORD']
MONGO_URI = os.environ['MONGOLAB_URI']
DB_NAME = urlparse.urlparse(MONGO_URI).path.strip('/')
MIN_COMMENTS = int(os.environ.get('IAMA_MIN_COMMENTS', 200))
WAIT_TIME = float(os.environ.get('IAMA_WAIT_TIME', 60.0))
MAX_COMMENT_LENGTH = 10000

BASE_URL = u'http://www.reddit.com/'
TIME_FORMAT = u"%b %d, %Y @ %I:%M:%S %P EST"

HEADER_FORMAT = (
  u'Most (if not all) of the answers from [{host}](/user/{host}/) (updated: {last_updated}):\n\n'
  u'*****\n'
)
SECOND_HEADER_FORMAT = (
  u'(page {page})\n\n'
  u'*****\n'
)
FOOTER = (
  u'(continued below)'
)
QA_FORMAT = (
  u'**[Question]({qlink}?context=1) ({asker}):**\n\n'
  u'{question}\n\n'
  u'**[Answer]({alink}?context=1) ({host}):**\n\n'
  u'{answer}\n\n'
  u'*****\n'
)
TOP_FORMAT = (
  u'**[Top-level Comment]({alink}):**\n\n'
  u'{answer}\n\n'
  u'*****\n'
)


def log(s):
  print s.encode('utf8')


def quotify(s):
  return u'> {}'.format(s.replace('\n', '\n> '))


def get_qa(first_comments, author):
  def helper(comments, parent=None):
    lst = []
    for comment in comments:
      if not isinstance(comment, narwal.things.Comment):
        continue
      if comment.author == author:
        if not parent or parent.author != USERNAME:
          lst.append((parent, comment))
      if comment.replies:
        lst += helper(comment.replies, comment)
    return lst
  qalst = helper(first_comments)
  if qalst:
    return sorted(qalst, key=lambda (p, c): c.created)
  else:
    return lst


def format_header(host):
  return HEADER_FORMAT.format(
    last_updated=time.strftime(TIME_FORMAT, time.localtime()),
    host=host
  )


def format_second_header(page):
  return SECOND_HEADER_FORMAT.format(
    page=page
  )


def format_top_level(answer):
  return TOP_FORMAT.format(
    alink=answer.permalink,
    answer=quotify(answer.body)
  )


def format_normal(host, question, answer):
  abody = answer.body
  if len(abody) > (MAX_COMMENT_LENGTH -
                   len(QA_FORMAT) -
                   len(HEADER_FORMAT) -
                   len(FOOTER)):
    abody = (
      u'{body} ...\n\n'
      u'(This answer was too long to fit.  [See the full response.]({link}))'
    ).format(
      answer.body.split('\n')[0][:100],
      answer.permalink
    )
  return QA_FORMAT.format(
    qlink=question.permalink,
    alink=answer.permalink,
    asker=question.author if question.author else u'[deleted]',
    question=quotify(question.body if question.body else u'[deleted]'),
    host=host,
    answer=quotify(abody)
  )


def format_qa(qalst, host, limit=MAX_COMMENT_LENGTH):
  if not qalst:
    return []
  
  pages = []
  sections = [format_header(host)]
  charcount = len(sections[0])
  page = 1
  move_on = False
  for question, answer in qalst:
    if question:
      s = format_normal(host, question, answer)
    else:
      s = format_top_level(answer)
    charcount += len(s) + 1
    if (page == 1 and move_on) or charcount >= (limit - len(FOOTER)):
      sections.append(FOOTER)
      pages.append(u'\n'.join(sections))
      page += 1
      header = format_second_header(page)
      sections = [header, s]
      charcount = len(s) + len(header) + 2
    else:
      sections.append(s)
      if page == 1:
        move_on = True
  if sections:
    pages.append(u'\n'.join(sections))
  return pages


def mysleep():
  log(u'Waiting {} seconds...'.format(WAIT_TIME))
  time.sleep(WAIT_TIME)


def process_iama(db, iama):
  log(u'Processing {} ...'.format(iama.permalink))
  host = iama.author
  comments = iama.comments()
  
  qalst = get_qa(comments, host)
  if not qalst:
    return
  sqalst = format_qa(qalst, host)
  
  query = {'link': iama.permalink}
  old_comp = db.comps.find_one(query)
  old_sqalst = old_comp['sqalst'] if old_comp else None
  
  new_sqalst = []
  rid = iama.name
  sleep = True
  try:
    for i, sqa in enumerate(sqalst):
      if old_sqalst and i < len(old_sqalst):
        rid = old_sqalst[i]['rid']
        if i == 0 or sqa != old_sqalst[i]['body']:
          c = iama._reddit.edit(rid, sqa)
          sleep = True
          log(u'Edited {}'.format(c.permalink))
        else:
          sleep = False
          log(u'No change: {}'.format(rid))
      else:
        c = iama._reddit.comment(rid, sqa)
        rid = c.name
        sleep = True
        log(u'Posted {}'.format(c.permalink))
      new_sqalst.append({'rid': rid,
                         'body': sqa})
      if sleep:
        mysleep()
  except Exception as e:
    raise e
  finally:
    log(u'Saving what we did to DB...')
    if old_sqalst and len(old_sqalst) > len(new_sqalst):
      new_sqalst = new_sqalst + old_sqalst[len(new_sqalst):]
    new_comp = {'link': iama.permalink,
                'sqalst': new_sqalst}
    db.comps.update(query, 
                    {'$set': new_comp},
                    upsert=True)
    log(u'... done.')
  log(u'Finished: {}'.format(iama.permalink))


def estimate_future_comments(link, now=None):
  now = now or time.time()
  return int((link.num_comments / (now - link.created_utc)) * (60 * 60) + link.num_comments)


def qualifies(iama):
  lower = iama.title.lower()
  return (estimate_future_comments(iama, time.time()) > MIN_COMMENTS and
          'ama request' not in lower and
          '[request]' not in lower and
          iama.author != u'[deleted]')


def relpath(path):
  if path.startswith(BASE_URL):
    path = path[len(BASE_URL):]
  return path


def main():
  connection = pymongo.Connection(MONGO_URI)
  db = connection[DB_NAME]
  api = narwal.connect(USERNAME, PASSWORD, user_agent='narwal_bot iama bot')
  if len(sys.argv) == 2:
    iama = api.get(relpath(sys.argv[1]))[0][0]
    process_iama(db, iama)
  else:
    iamas = [iama for iama in api.hot('iama') if qualifies(iama)]
    log(u'Processing {} IAMAs...'.format(len(iamas)))
    for iama in iamas:
      process_iama(db, iama)
    log(u'Processing done.'.encode('utf8'))


if __name__ == "__main__":
  main()