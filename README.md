reddit-iama-bot
===============

A python bot that makes reading answers from reddit IAMAs easier by compiling them into an easy-to-read list and posting it into the original IAMA.

You can see it in action at [reddit.com/r/iama](http://reddit.com/r/iama) or [my bot's user page](http://reddit.com/user/narwal_bot).

**Don't run your own instance of this bot, please.  /r/iama ain't big enough for two of these bots.**


go.py
-----

Running `python go.py` basically does this:

1. Gets the hottest 25 IAMAs from r/iama.
2. Reduces the list down to those that will likely have at least a minimum number of comments (currently 200).
3. For each IAMA in the list:
   * compiles a list of questions and answers
   * posts the list in the IAMA as a chain of comments

The script tries to do this efficiently with as few requests possible.  To do so, it requires a MongoDB instance to store its previous comments.  See the source for more details.


the bot
-------

The bot is set up on **[Heroku](https://devcenter.heroku.com/articles/python)** with the **[MongoLab Starter add-on](https://devcenter.heroku.com/articles/mongolab)** and **[Heroku Scheduler add-on](https://devcenter.heroku.com/articles/scheduler)** (all for free!).  Running `heroku config` includes lines:

    IAMA_MIN_COMMENTS => 200
    IAMA_WAIT_TIME    => 60
    MONGOLAB_URI      => mongodb://...
    REDDIT_PASSWORD   => <password>
    REDDIT_USERNAME   => narwal_bot
    SCHEDULER_URL     => http://...
    TZ                => US/Eastern
    USER_AGENT        => <user_agent>

The Scheduler is set to run `python go.py` every hour.  Technically, it runs the `go` process, which is defined in the `Procfile` as `python go.py`.  This is necessary because running the script is a [long-running job](https://devcenter.heroku.com/articles/scheduler#longrunning_jobs).


narwal
------

The bot uses [narwal](https://github.com/larryng/narwal) extensively.  [narwal](https://github.com/larryng/narwal) is an open source python reddit API wrapper that I wrote.  [Go check it out](https://github.com/larryng/narwal)!