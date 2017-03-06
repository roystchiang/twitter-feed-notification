# twitter-feed-notification

The goal of this project is to detect whether there is an event on twitter that
is worth reporting to the user. The project is separated into three sections.

1. crawler.py
2. streamer.py
3. machine_learning.py

## crawler.py

Crawler goes through a given list of twitter handles, and retrieves the tweets
using ``@user_handle``.

## streamer.py

Stream contains two main classes. ``OfflineStreamer`` and ``Streamer``.
``Streamer`` is suppose to stream from the twitter API into another service that handles all
the incoming tweets, and ``OfflineStreamer`` is suppose to mock ``Streamer``
but using data from ``tweets.json``

## machine_learning.py

This file is the meat of the project. All tweets are first preprocessed, then
clustered by topics, and a notifier decides whether to send notification or
not.

### Preprocessing

All of the tweets in reply to another user is removed, and all retweets are
removed.

### Clustering

Two clustering methods are implemented, NMF and KMeans. One of the benefits of
KMeans is that we can use bagging until all "best tweets" from the largest
cluster converge into a single "tweet"

### Notifier

Right now, it's an extremely simply class that just looks at the average amount
of tweet, and if there are 3 times more tweets than the average amount of
tweets, twe notify the user.

A better approach would be to look at the time and day, since there would
probably be less tweets at night and on the weekends as well.
