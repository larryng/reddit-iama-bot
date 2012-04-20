#!/usr/bin/python

import sys
import time
import narwal


AUTHOR = ''

def quotify(s):
  return u'> {}'.format(s.replace('\n', '\n> '))

def get_qa(first_comments, author):
  def helper(comments, parent=None):
    lst = []
    for comment in comments:
      if not isinstance(comment, narwal.things.Comment):
        continue
      if comment.author == author:
        lst.append((parent, comment))
      if comment.replies:
        lst += helper(comment.replies, comment)
    return lst
  lst = helper(first_comments)
  return sorted(lst, key=lambda (p, c): c.created)

def format_qa(lst, limit=10000):
  rlst = []
  slst = [u'Last updated: {}\n'.format(time.strftime("%b %d, %Y @ %I:%M:%S %P EST", time.localtime())),
          u'The following is an automated compilation of answers from the IAMA host:\n']
  charcount = 0
  for q, a in lst:
    if q:
      s = (u'**[Question]({qlink}) ({asker}):**\n\n'
           u'{question}\n\n'
           u'**Answer:**\n\n'
           u'{answer}\n\n'
           u'*****\n').format(qlink=q.permalink,
                              asker=q.author if hasattr(q, 'author') else u'[deleted]',
                              question=quotify(q.body if hasattr(q, 'body') else u'[deleted]'),
                              answer=quotify(a.body))
    else:
      s = (u'**Top-level Comment:**\n\n'
           u'{answer}\n\n').format(answer=quotify(a.body))
    charcount += len(s)
    if charcount >= limit:
      rlst.append('\n'.join(slst))
      slst = [s]
      charcount = len(s)
    else:
      slst.append(s)
  if slst:
    rlst.append('\n'.join(slst))
  return rlst

def compile(api, path):
  global AUTHOR
  listblob = api.get(path)
  link = listblob[0][0]
  comments = listblob[1]
  qa = get_qa(comments, link.author)
  sqa = format_qa(qa)
  AUTHOR = link.author
  return sqa

BASE_URL = u'http://www.reddit.com/'
def main():
  global AUTHOR
  if len(sys.argv) == 2:
    api = narwal.connect('narwal_bot', 'wordpass', user_agent='narwal_bot iama bot')
    path = sys.argv[1]
    if path.startswith(BASE_URL):
      path = path[len(BASE_URL):]
    for i, s in enumerate(compile(api, path)):
      with open('{}{}.txt'.format(AUTHOR, i), 'w') as f:
        f.write(s)
  else:
    print 'wrong args'

if __name__ == "__main__":
  main()