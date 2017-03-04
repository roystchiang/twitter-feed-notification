import json
import multiprocessing
import settings
import tweepy

class Streamer(multiprocessing.Process):
    """
    Worker for streaming a given user's tweets
    """

    def __init__(self, file_name, offline=False):
        multiprocessing.Process.__init__(self)
        self.offline = offline
        self.file_name = file_name

    def run(self):
        proc_name = self.name
        print "Streaming {}".format(self.offline)


class OfflineTweets(object):
    """
    A fake tweeter stream
    """
    def __init__(self, file_name):
        self.file_name = file_name
        self.tweets = []
        self.initialize_tweets()
        for tweet in self.tweets:
            print tweet['created_at']


    def initialize_tweets(self):
        with open(self.file_name) as f:
            for line in f:
                data = json.loads(line)
                self.tweets.append(data)
        self.tweets = sorted(self.tweets, key=lambda tweet: tweet['created_at'])


if __name__ == "__main__":
    print "Now streaming tweets"
    streamer = Streamer(True)
    offline_tweets = OfflineTweets("tweets.json")
    streamer.start()
