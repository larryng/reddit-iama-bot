#!/usr/bin/python
# -*- coding: utf8 -*- 

import os
import sys
import time
import narwal
import pymongo
import urlparse


USER_AGENT = os.environ['USER_AGENT']
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
  u'{qbody}\n\n'
  u'**[Answer]({alink}?context=1) ({host}):**\n\n'
  u'{abody}\n\n'
  u'*****\n'
)
TOP_FORMAT = (
  u'**[Top-level Comment]({alink}):**\n\n'
  u'{answer}\n\n'
  u'*****\n'
)


def get_db():
  connection = pymongo.Connection(MONGO_URI)
  return connection[DB_NAME]


def log(s):
  print s.encode('utf8') # heroku can't log unicode


def quotify(s):
  """reddit markdown quotes a string"""
  return u'> {}'.format(s.replace('\n', '\n> '))


def get_qalst(host, first_comments):
  """returns list of (question, answer) comment pairs
  
  parameters:
  - host: string username of iama host
  - first_comments: top-level comments listing, ie. iama.comments()"""
  def helper(comments, parent=None):
    lst = []
    for comment in comments:
      if not isinstance(comment, narwal.things.Comment):
        continue
      if comment.author == host:
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
  """formats header for our bot's first comment"""
  return HEADER_FORMAT.format(
    last_updated=time.strftime(TIME_FORMAT, time.localtime()),
    host=host
  )


def format_second_header(page):
  """formats header for our bot's subsequent comments"""
  return SECOND_HEADER_FORMAT.format(
    page=page
  )


def format_top_level(answer):
  """formats host's top-level comment"""
  return TOP_FORMAT.format(
    alink=answer.permalink,
    answer=quotify(answer.body)
  )


def format_normal(host, question, answer):
  """formats question/answer pair"""
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
    qbody=quotify(question.body if question.body else u'[deleted]'),
    host=host,
    abody=quotify(abody)
  )


def generate_pages(host, qalst, limit=MAX_COMMENT_LENGTH):
  """generates a list of pages from a list of question/answer pairs, where each page is to be posted as a comment"""
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
  """just time.sleep() with a log message"""
  log(u'Waiting {} seconds...'.format(WAIT_TIME))
  time.sleep(WAIT_TIME)


def post_pages(iama, pages, db=None):
  """post the generated comments to the iama, ensuring that:
    a. we don't spam with duplicate comments if we already processed this iama
    b. if we already processed the iama, update/edit the comment instead of
       posting again
    c. don't make an edit if nothing changed (reduce POST requests to reduce
       chance we get rate-limited)
  """
  if not db:
    db = get_db()
  
  # get the old generated pages from our database
  query = {'link': iama.permalink}
  old_comp = db.comps.find_one(query) # 'comp' as in 'compilation'
  old_pages = old_comp['pages'] if old_comp else None
  
  new_pages = []
  rid = iama.name # reddit id (aka. "full name") of the thing to comment to or
                  # edit.  it may seem odd at first that the same variable is
                  # used for both of these situations, but it makes sense if you
                  # follow the logic.
  try:
    for i, page in enumerate(pages):
      sleep = True
      if old_pages and i < len(old_pages):
        rid = old_pages[i]['rid']
        if page != old_pages[i]['body']:
          c = iama._reddit.edit(rid, page)
          log(u'Edited {}'.format(c.permalink))
        else:
          sleep = False
          log(u'No change: {}'.format(rid))
      else:
        c = iama._reddit.comment(rid, page)
        rid = c.name
        log(u'Posted {}'.format(c.permalink))
      new_pages.append({'rid': rid,
                        'body': page})
      if sleep:
        mysleep() # sleep after POSTs so we don't get rate limited
  except Exception as e:
    # just crash if something goes wrong.  it's not the end of the world if we
    # miss an update.
    raise e
  finally:
    log(u'Saving what we did to DB...')
    
    # don't lose old data if something went awry while processing
    if old_pages and len(old_pages) > len(new_pages):
      new_pages = new_pages + old_pages[len(new_pages):]
    
    # save to db
    new_comp = {'link': iama.permalink,
                'pages': new_pages}
    db.comps.update(query, 
                    {'$set': new_comp},
                    upsert=True)
    log(u'... done.')


def process_iama(iama, db=None):
  """processes an iama:
  
  1. aggregate list of question/answer pairs from the iama
  2. from that list, generate the comments to be posted
  3. post the generated comments to the iama
  """
  log(u'Processing {} ...'.format(iama.permalink))
  host = iama.author
  comments = iama.comments()
  
  # aggregate list of q/a pairs from the iama
  qalst = get_qalst(host, comments)
  if not qalst:
    return
  
  # generate our comments to be posted
  pages = generate_pages(host, qalst)
  
  post_pages(iama, pages, db=db)
  log(u'Finished: {}'.format(iama.permalink))


def estimate_future_comments(link, now=None):
  """linear estimate of the number of comments the iama will have in 1 hour"""
  now = now or time.time()
  comments_per_second = link.num_comments / (now - link.created_utc)
  return int(link.num_comments + comments_per_second * 3600)


def qualifies(iama):
  """returns true if iama qualifies to be processed.
  
  iama qualifies if all of the following are true:
    - it will likely have over MIN_COMMENTS within the next hour
    - it is not an ama request
    - the iama host account still exists (i.e. wasn't deleted)
  """
  lower = iama.title.lower()
  return (
    estimate_future_comments(iama, time.time()) > MIN_COMMENTS and
    'ama request' not in lower and
    '[request]' not in lower and
    iama.author != u'[deleted]'
  )


def relpath(path):
  """takes a reddit path and returns the relative path"""
  if path.startswith(BASE_URL):
    path = path[len(BASE_URL):]
  return path


def main():
  # establish db and reddit connections
  db = get_db()
  api = narwal.connect(USERNAME, PASSWORD, user_agent=USER_AGENT)
  
  # given a url, process it.
  # otherwise, process all qualifying iamas on r/iama's frontpage
  if len(sys.argv) == 2:
    # this will actually make an extra request, but oh well.  it's just for
    # testing process_iama() and is not a problem in production
    iama = api.get(relpath(sys.argv[1]))[0][0]
    process_iama(iama, db=db)
  else:
    iamas = [iama for iama in api.hot('iama') if qualifies(iama)]
    log(u'Processing {} IAMAs...'.format(len(iamas)))
    for iama in iamas:
      process_iama(iama, db=db)
    log(u'Processing done.'.encode('utf8'))


if __name__ == "__main__":
  main()
  pass