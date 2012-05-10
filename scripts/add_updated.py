# -*- coding: utf8 -*-

import os
import sys

sys.path.insert(0, os.path.abspath('..'))

import re
import datetime

from iama.utils import get_db


TIME_FORMAT = u'%b %d, %Y @ %I:%M:%S %p EST'
PATTERN = re.compile(r'\(updated: (.+?)\)')


def grab_updated(comp):
    s = comp['pages'][0]['body']
    m = PATTERN.search(s)
    return datetime.datetime.strptime(m.group(1), TIME_FORMAT)


def main():
    db = get_db()
    
    for c in db.comps.find():
        updated = grab_updated(c)
        c['updated'] = updated
        db.comps.save(c)
        print u'Done: {0} ({1})'.format(c['link'], updated)


if __name__ == '__main__':
    main()
    pass