import numpy as np
import pandas as pd
import json
import nltk
import random
import settings
import sklearn
from collections import Counter
from datetime import timedelta
from datetime import datetime
from sklearn.decomposition import NMF
from sklearn.cluster import KMeans


class Preprocessing(object):
    def __init__(self):
        """
        Args:
            tweets - A list of tweets
        """
        pass

    def process(self):
        """Perform tweet preprocessing"""
        self.tweets = [ tweet for tweet in self.tweets
                        if self.retweet_filter(tweet) ]

    def retweet_filter(self, text):
        """Returns True if the tweet isn't a retweet"""
        return not text.lower().startswith('rt')

    def user_reply_filter(self, text):
        """Returns True if the tweet isn't start with ``@``"""
        return not text.lower().startswith('@')

    def filter(self, text):
        return self.retweet_filter(text) and self.user_reply_filter(text)


    def result(self):
        return self.tweets


class TopicModeller(object):
    """
    Wrapper for handling multiple learning types
    """

    def __init__(self, df, learner):
        """
        Args:
            dataframe - A pd.DataFrame to train
            learner - A class that implements .fit()
        """
        self.df = df
        self.learner = learner
        self.vectorizer = sklearn.feature_extraction.text.TfidfVectorizer(
                            tokenizer=self.tokenizer, use_idf=True)
        self.preprocess()

    def preprocess(self):
        helper = Preprocessing()
        self.df = self.df[self.df.apply(lambda x: helper.filter(x['text']), axis=1)]

    @staticmethod
    def tokenizer(text):
        """
        Args:
            text - A string
        """
        stop_words = set(nltk.corpus.stopwords.words('english'))
        stop_words.update(('@', ':', 'https', ',', '.', 'rt', '#', '!', '&'
                          'cnn', 'bbcnews', 'telegraph', 'cnet', '?') +
                         tuple(settings.feeds))
        tokens = nltk.word_tokenize(text)
        return [word.lower() for word in tokens if word not in stop_words]

    def common_words(self):
        feature_names = self.vectorizer.get_feature_names()
        return [[feature_names[i] for i in topic.argsort()[:-9:-1]] for topic in self.model.components_]

    def _modelling(self, tfidf):
        feature_names = self.vectorizer.get_feature_names()
        return self.learner.fit(tfidf)

    def fit(self):
        tfidf_matrix = self.vectorizer.fit_transform(self.df['text'])
        self.model = self._modelling(tfidf_matrix)


class NMFCluster(TopicModeller):

    def cluster_counter(self):
        return None
    
    def common_words(self):
        feature_names = self.vectorizer.get_feature_names()
        return [[feature_names[i] for i in topic.argsort()[:-9:-1]] for topic in self.model.components_]


class KMeansCluster(TopicModeller):
    
    def cluster_counter(self):
        """Returns a Counter of the clusters"""
        return Counter(self.model.labels_.tolist())

    def common_words(self):
        """Returns common words of each cluster"""
        order_centroids = self.model.cluster_centers_.argsort()[:, ::-1]
        clusters = self.model.labels_.tolist()
        vocab = self.vectorizer.vocabulary_
        return [ [vocab.keys()[vocab.values().index(i)] for i in
                  order_centroids[cluster, :10]] for cluster in sorted(set(clusters))]


class BestTweet(object):
    """
    This is a simple implmentation for determining the best tweet for each
    topic. A better model could include the consideration of retweets,
    time of tweet, and other variables
    """

    def __init__(self, df, topics):
        self.df = df
        self.topics = topics

    @staticmethod
    def _get_score(text, words):
        return sum([(word in text) * i / 100.0 for i, word in enumerate(words)])

    def _get_best_tweet(self, words):
        best_tweet_index = self.df['text'].apply(lambda text: self._get_score(text, words)).idxmax()
        return self.df.loc[best_tweet_index]

    def best_tweet(self):
        return [self._get_best_tweet(topic) for topic in self.topics]

class Notifier(object):
    """Right now, the notifier simply checks whether or not the number of
    tweets given in a timeframe is significantly more than the average tweets
    in the same timeframe
    """

    def __init__(self, df):
        temp_df = tweet_df.set_index('created_at')
        self.average_tweet_frequency = temp_df.groupby(pd.TimeGrouper(freq='15Min'))['text'].count().mean()
        self.file_name = "notifications.json"

    def tweet_deserializer(self, tweet):
        """
        Args:
            tweet - A series containing ``created_at``, ``id``, and ``text``
        """
        return json.dumps({"id": tweet['id'],
                           "text": tweet['text'],
                           "tweeted_at": tweet['created_at'].isoformat(),
                           "notified_on": datetime.now().isoformat()}) + "\n"
        

    def notify(self, tweet_size, cluster_counter, best_tweets):
        if tweet_size > 3 * self.average_tweet_frequency:
            largest_cluster = cluster_counter.most_common(1)[0][0]
            best_tweet = best_tweets[largest_cluster]

            notification_file = open(self.file_name, 'a')
            notification_file.write(self.tweet_deserializer(best_tweet))
            notification_file.close()
            return best_tweet
        else:
            return None


def random_sample(dataframe):
    """
    Returns a dataframe containing all tweets within 15 minutes from each other
    """
    index = random.randint(0, len(dataframe))
    created_at = dataframe.loc[index]['created_at']
    return dataframe[dataframe["created_at"] < created_at][dataframe["created_at"] > created_at - timedelta(minutes=15)]


if __name__ == "__main__":
    print "Started Machine Learning"
    tweet_df = pd.read_json("tweets.json", lines=True)
    sample_tweets = random_sample(tweet_df)

    # start clustering and get common words
    nmf_cluster = NMFCluster(sample_tweets, NMF(n_components=10))
    nmf_cluster.fit()
    kmeans_cluster = KMeansCluster(sample_tweets, KMeans(n_clusters=10))
    kmeans_cluster.fit()

    # get the common words from each cluster
    nmf_cluster.common_words()
    kmeans_cluster.common_words()

    # get the best tweet from each cluster
    nmf_best_tweet = BestTweet(sample_tweets, nmf_cluster.common_words()).best_tweet()
    kmeans_best_tweet = BestTweet(sample_tweets, kmeans_cluster.common_words()).best_tweet()

    # find teh largest cluster
    notifier = Notifier(tweet_df)
    notifier.notify(len(sample_tweets), kmeans_cluster.cluster_counter(), kmeans_best_tweet)
