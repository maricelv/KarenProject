import twitter
from functools import partial
from sys import maxsize as maxint
import sys
import time
from urllib.error import URLError
from http.client import BadStatusLine
from transformers import pipeline


CONSUMER_KEY = ''
CONSUMER_SECRET = ''
OAUTH_TOKEN = ''
OAUTH_TOKEN_SECRET = ''
    

auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
                                       CONSUMER_KEY, CONSUMER_SECRET)

api = twitter.Twitter(auth=auth)
# #Function taken from TwitterCookbook
def make_twitter_request(twitter_api_func, max_errors=10, *args, **kw): 
    
    # A nested helper function that handles common HTTPErrors. Return an updated
    # value for wait_period if the problem is a 500 level error. Block until the
    # rate limit is reset if it's a rate limiting issue (429 error). Returns None
    # for 401 and 404 errors, which requires special handling by the caller.
    def handle_twitter_http_error(e, wait_period=2, sleep_when_rate_limited=True):
    
        if wait_period > 3600: # Seconds
            print('Too many retries. Quitting.', file=sys.stderr)
            raise e
    
        # See https://developer.twitter.com/en/docs/basics/response-codes
        # for common codes
    
        if e.e.code == 401:
            print('Encountered 401 Error (Not Authorized)', file=sys.stderr)
            return None
        elif e.e.code == 404:
            print('Encountered 404 Error (Not Found)', file=sys.stderr)
            return None
        elif e.e.code == 429: 
            print('Encountered 429 Error (Rate Limit Exceeded)', file=sys.stderr)
            if sleep_when_rate_limited:
                print("Retrying in 15 minutes...ZzZ...", file=sys.stderr)
                sys.stderr.flush()
                time.sleep(60*15 + 5)
                print('...ZzZ...Awake now and trying again.', file=sys.stderr)
                return 2
            else:
                raise e # Caller must handle the rate limiting issue
        elif e.e.code in (500, 502, 503, 504):
            print('Encountered {0} Error. Retrying in {1} seconds'                  .format(e.e.code, wait_period), file=sys.stderr)
            time.sleep(wait_period)
            wait_period *= 1.5
            return wait_period
        else:
            raise e

    # End of nested helper function
    
    wait_period = 2 
    error_count = 0 

    while True:
        try:
            return twitter_api_func(*args, **kw)
        except twitter.api.TwitterHTTPError as e:
            error_count = 0 
            wait_period = handle_twitter_http_error(e, wait_period)
            if wait_period is None:
                return
        except URLError as e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print("URLError encountered. Continuing.", file=sys.stderr)
            if error_count > max_errors:
                print("Too many consecutive errors...bailing out.", file=sys.stderr)
                raise
        except BadStatusLine as e:
            error_count += 1
            time.sleep(wait_period)
            wait_period *= 1.5
            print("BadStatusLine encountered. Continuing.", file=sys.stderr)
            if error_count > max_errors:
                print("Too many consecutive errors...bailing out.", file=sys.stderr)
                raise

# Sample usage

twitter_api = api

#Function taken from TwitterCookbook
def harvest_user_timeline(twitter_api, screen_name=None, user_id=None, max_results=1000):
     
    assert (screen_name != None) != (user_id != None),     "Must have screen_name or user_id, but not both"    
    
    kw = {  # Keyword args for the Twitter API call
        'count': 200,
        'trim_user': 'true',
        'include_rts' : 'true',
        'since_id' : 1
        }
    
    if screen_name:
        kw['screen_name'] = screen_name
    else:
        kw['user_id'] = user_id
        
    max_pages = 16
    results = []
    
    tweets = make_twitter_request(twitter_api.statuses.user_timeline, **kw)
    
    if tweets is None: # 401 (Not Authorized) - Need to bail out on loop entry
        tweets = []
        
    results += tweets
    
   # print('Fetched {0} tweets'.format(len(tweets)), file=sys.stderr)
    
    page_num = 1
    
    # Many Twitter accounts have fewer than 200 tweets so you don't want to enter
    # the loop and waste a precious request if max_results = 200.
    
    # Note: Analogous optimizations could be applied inside the loop to try and 
    # save requests. e.g. Don't make a third request if you have 287 tweets out of 
    # a possible 400 tweets after your second request. Twitter does do some 
    # post-filtering on censored and deleted tweets out of batches of 'count', though,
    # so you can't strictly check for the number of results being 200. You might get
    # back 198, for example, and still have many more tweets to go. If you have the
    # total number of tweets for an account (by GET /users/lookup/), then you could 
    # simply use this value as a guide.
    
    if max_results == kw['count']:
        page_num = max_pages # Prevent loop entry
    
    while page_num < max_pages and len(tweets) > 0 and len(results) < max_results:
    
        # Necessary for traversing the timeline in Twitter's v1.1 API:
        # get the next query's max-id parameter to pass in.
        # See https://dev.twitter.com/docs/working-with-timelines.
        kw['max_id'] = min([ tweet['id'] for tweet in tweets]) - 1 
    
        tweets = make_twitter_request(twitter_api.statuses.user_timeline, **kw)
        results += tweets

    #    print('Fetched {0} tweets'.format(len(tweets)),file=sys.stderr)
    
        page_num += 1
        
    print('Done fetching tweets', file=sys.stderr)

    return results[:max_results]
    

#Start of Script

# Looking for Twitter users that have that name
userName= "Mary" 
# This prints out tweets and tweet statistics to a text file 
sys.stdout = open('tweets.txt', 'w') 
# This makes a clean text file each time its run so save the data if you need it later
sys.stdout.close() 

# Getting users with userName in their twitter handle/name
# Each iteration of results gets the Maximum number of 20 users, hence why we call it 5 times
results = twitter_api.users.search(q=userName, page=1)
results2 = twitter_api.users.search(q=userName, page=2)
results3 = twitter_api.users.search(q=userName, page=3)
results4 = twitter_api.users.search(q=userName, page=4)
results5 = twitter_api.users.search(q=userName, page=5)

# From the accounts that we just mined, we grab their screen_name and location 
tweets1 = [(r['screen_name'], r['location']) for r in results]
tweets2 = [(r['screen_name'], r['location']) for r in results2]
tweets3 = [(r['screen_name'], r['location']) for r in results3]
tweets4 = [(r['screen_name'], r['location']) for r in results4]
tweets5 = [(r['screen_name'], r['location']) for r in results5]

# Combining this information into one giant List
tweets1.extend(tweets2)
tweets1.extend(tweets3)
tweets1.extend(tweets4)
tweets1.extend(tweets5)

# These variables will track total tweets, positive and negative tweets, as well as the confidence score
tweetCount = 0
posCount = 0
negCount = 0
confidenceScore = 0

sentimentanalyzer = pipeline("sentiment-analysis")

for (name,location) in tweets1:
            karenTweets = harvest_user_timeline(twitter_api, screen_name=name, max_results=500) #Gathering the 500 most recent tweets from the given screen_name
            sys.stdout = open('tweets.txt', 'a') #appending information to the text file
            print("//////////////////////////////////////////NEXT USER/////////////////////////////////")
            print(name) 
            print(location.encode('utf8'))          
            for i, t in enumerate(karenTweets): # Parsing through the user's tweets
                if ('Trump' in t['text'] or 'Biden' in t['text']): # This is where we insert keywords to filter the tweets through, in this case for out Presidents category
                    # if (not t['retweeted'] and 'RT @' not in t['text']): # We had this line for when we wanted to see only original tweets
                        try:  
                                tweetCount = tweetCount + 1 
                                d = sentimentanalyzer(t['text']) # Transformers package performing sentiment analysis on the tweet
                                tweetLabel = d[0].get('label') # Gets the label
                                tweetScore = d[0].get('score') # Gets the confidence score
                                if (tweetLabel=='POSITIVE'):
                                    posCount = posCount + 1
                                else:
                                    negCount = negCount + 1
                                confidenceScore = confidenceScore + float(tweetScore)
                                print("\n")                                
                                print(i, t['text'].encode('utf8')) # prints out the tweet
                                print(d) # prints out the label and confidence score
                        except:
                                pass
        

averageScore = confidenceScore / float(tweetCount) # calculates average confidence score for all tweets from harvested users
positiveScore = (posCount / tweetCount) * 100 # calculates the percentage of tweets that were positive
print(f"This program read {tweetCount} tweets")
print(f"Number of Positive Tweets is:{posCount}")
print(f"Number of Number of Tweets is:{negCount}")
print(f"{positiveScore}% of the tweets are positive")
print(f"The average confidence score is:{averageScore}")
sys.stdout.close()
