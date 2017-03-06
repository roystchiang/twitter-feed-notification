import json
from datetime import datetime
import multiprocessing
import settings
import tweepy

class Streamer(object):
    """
    Worker for streaming a given user's tweets
    """

    def __init__(self, offline_tweet=None):
        self.offline_tweet = offline_tweet

    def _offline_runner(self):
        while True:
            tweet = self.offline_tweet.get_tweet()
            if tweet:
                print tweet
            else:
                break

    def run(self):
        if self.offline_tweet:
            self._offline_runner()


class OfflineTweets(object):
    """
    A fake tweeter stream
    """
    def __init__(self, file_name):
        self.file_name = file_name
        self.tweets = []
        self.initialize_tweets()

    def _isotime_parser(self, time):
        """
        Args:
            time - A string
        Returns a datetime object
        """
        return datetime.strptime(time, "%Y-%m-%dT%H:%M:%S")

    def initialize_tweets(self):
        with open(self.file_name) as f:
            for line in f:
                data = json.loads(line)
                data['created_at'] = self._isotime_parser(data['created_at'])
                self.tweets.append(data)
        self.tweets = sorted(self.tweets, key=lambda tweet: tweet['created_at'])

    def get_tweet(self):
        if len(self.tweets):
            return self.tweets.pop(0)
        else:
            return None


if __name__ == "__main__":
    print "Now streaming tweets"
    offline_tweets = OfflineTweets("tweets.json")
    streamer = Streamer(offline_tweets)
    streamer.run()
