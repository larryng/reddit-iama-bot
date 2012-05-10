# -*- coding: utf8 -*- 

import os
import sys
import urlparse

USER_AGENT = os.environ['USER_AGENT']
USERNAME = os.environ['REDDIT_USERNAME']
PASSWORD = os.environ['REDDIT_PASSWORD']
MONGO_URI = os.environ['MONGOLAB_URI']
DB_NAME = urlparse.urlparse(MONGO_URI).path.strip('/')
MIN_COMMENTS = int(os.environ.get('IAMA_MIN_COMMENTS', 200))
WAIT_TIME = float(os.environ.get('IAMA_WAIT_TIME', 60.0))