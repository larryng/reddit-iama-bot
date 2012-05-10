# -*- coding: utf8 -*-

import os
import sys
import pymongo

sys.path.insert(0, os.path.abspath('..'))

from iama.utils import get_db


def main():
    if len(sys.argv) == 1:
        limit = 0
    else:
        limit = int(sys.argv[1])
    db = get_db()
    for c in db.comps.find(sort=[('updated', pymongo.ASCENDING)], limit=limit):
        print u'http://www.reddit.com{0}{1}'.format(c['link'], c['pages'][0]['rid'][3:])


if __name__ == '__main__':
    main()
    pass