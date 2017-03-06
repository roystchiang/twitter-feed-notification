from datetime import datetime
import json
import multiprocessing
import settings
import tweepy
import time

auth = tweepy.OAuthHandler(settings.twitter_consumer_key,
                           settings.twitter_consumer_secret)
auth.set_access_token(settings.twitter_access_token,
                      settings.twitter_access_secret)
api = tweepy.API(auth)

class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return json.JSONEncoder.default(self, obj)

class TweetQueueWorker(multiprocessing.Process):
    """
    Worker for TweetQueue
    """
    def __init__(self, tweet_queue, worker_count):
        """
        Args:
            tweet_queue - A multiprocessing.JoinableQueue()
            worker_count - The number of workers working on the tweet_queue
        """
        multiprocessing.Process.__init__(self)
        self.tweet_queue = tweet_queue
        self.worker_count = worker_count
        self.file_name = "tweets.json"
        self.tweet_map = {}

        # initalize properties
        self.initialize_map()

    def initialize_map(self):
        """
        Initialize self.tweet_map to a tweet ids
        """
        with open(self.file_name) as f:
            for line in f:
                data = json.loads(line)
                self.tweet_map[data['id']] = data['text']

    def run(self):
        poison_count = 0
        tweet_file = open(self.file_name, 'a')

        while poison_count < self.worker_count:
            tweet = self.tweet_queue.get()
            if tweet == None:
                poison_count += 1
            else:
                content = self._tweet_status_parser(tweet)
                self._write_to_file(tweet_file, content)

            self.tweet_queue.task_done()
        return

    def _write_to_file(self, file_object, content):
        """
        Args:
            file_object - The file to be written to
            content - A dictionary
        """
        if content['id'] not in self.tweet_map:
            file_object.write(json.dumps(content, cls=JsonEncoder)+'\n')
        return

    def _tweet_status_parser(self, tweet_status):
        """
        Args:
            tweet_status - A Tweepy.Status object
        """
        return {'id': tweet_status.id,
                'text': tweet_status.text,
                'created_at': tweet_status.created_at}



class CrawlQueueWorker(multiprocessing.Process):
    """
    Worker for CrawlQueue
    """
    def __init__(self, crawl_queue, tweet_queue):
        """
        Args:
            crawl_queue - A multiprocessing.JoinableQueue()
            tweet_queue - A multiprocessing.JoinableQueue(), containing
                          Tweepy.Status objects
        """
        multiprocessing.Process.__init__(self)
        self.crawl_queue = crawl_queue
        self.tweet_queue = tweet_queue

    def run(self):
        while True:
            twitter_user = self.crawl_queue.get()
            if twitter_user == None:
                print "Ending"
                self.tweet_queue.put(None)
                self.crawl_queue.task_done()
                break
            else:
                self.crawl_queue.task_done()
                print "{}: Crawling @{}".format(self.name, twitter_user)
                self._crawl_twitter(twitter_user)
        return

    def _crawl_twitter(self, user):
        try:
            for status in tweepy.Cursor(api.search,
                                        q="@"+user+" since:2017-03-02" + " until:2017-03-04").items():
                self.tweet_queue.put(status)
        except tweepy.TweepError as e:
            print "{}: {}, {}".format(self.name, user, e)
        return
        

if __name__ == "__main__":
    # initialize common variables
    crawl_queue_worker_count = 1

    # initalize queues
    crawl_queue = multiprocessing.JoinableQueue()
    tweet_queue = multiprocessing.JoinableQueue()

    # add all requred feeds into the queue
    for twitter_user in settings.feeds:
        crawl_queue.put(twitter_user)
    for i in range(crawl_queue_worker_count):
        crawl_queue.put(None)

    # start crawler workers
    crawl_queue_workers = [ CrawlQueueWorker(crawl_queue, tweet_queue)
                            for i in range(crawl_queue_worker_count) ]
    for crawler in crawl_queue_workers:
        crawler.start()

    # start tweet queue worker
    tweet_queue_worker = TweetQueueWorker(tweet_queue, crawl_queue_worker_count)
    tweet_queue_worker.start()

    # wait for both queues to complete
    tweet_queue.join()
    crawl_queue.join()
