import twitter
from functools import partial
from sys import maxsize as maxint
import sys
import time
from urllib.error import URLError
from http.client import BadStatusLine
import json
import networkx as nx
import matplotlib.pyplot as plt




auth = twitter.oauth.OAuth(OAUTH_TOKEN, OAUTH_TOKEN_SECRET,
                                       CONSUMER_KEY, CONSUMER_SECRET)

api = twitter.Twitter(auth=auth)
# From Cookbook
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

# See http://bit.ly/2Gcjfzr for twitter_api.users.lookup

#response = make_twitter_request(twitter_api.users.lookup, 
                                #screen_name="marceyreads")

#print(json.dumps(response, indent=1))
# From Cookbook
def get_friends_followers_ids(twitter_api, screen_name=None, user_id=None,
                              friends_limit=maxint, followers_limit=maxint):
    
    # Must have either screen_name or user_id (logical xor)
    assert (screen_name != None) != (user_id != None),     "Must have screen_name or user_id, but not both"
    
    # See http://bit.ly/2GcjKJP and http://bit.ly/2rFz90N for details
    # on API parameters
    
    get_friends_ids = partial(make_twitter_request, twitter_api.friends.ids, 
                              count=5000)
    get_followers_ids = partial(make_twitter_request, twitter_api.followers.ids, 
                                count=5000)

    friends_ids, followers_ids = [], []
    
    for twitter_api_func, limit, ids, label in [
                    [get_friends_ids, friends_limit, friends_ids, "friends"], 
                    [get_followers_ids, followers_limit, followers_ids, "followers"]
                ]:
        
        if limit == 0: continue
        
        cursor = -1
        while cursor != 0:
        
            # Use make_twitter_request via the partially bound callable...
            if screen_name: 
                response = twitter_api_func(screen_name=screen_name, cursor=cursor)
            else: # user_id
                response = twitter_api_func(user_id=user_id, cursor=cursor)

            if response is not None:
                ids += response['ids']
                cursor = response['next_cursor']
        
            print('Fetched {0} total {1} ids for {2}'.format(len(ids),                  label, (user_id or screen_name)),file=sys.stderr)
        
            # XXX: You may want to store data during each iteration to provide an 
            # an additional layer of protection from exceptional circumstances
        
            if len(ids) >= limit or response is None:
                break

    # Do something useful with the IDs, like store them to disk...
    return friends_ids[:friends_limit], followers_ids[:followers_limit]



# Reciprocal Friends
def reciprocal_friends(friends_ids, followers_ids):
    set3 = set(friends_ids) 
    set2= set(followers_ids) #find the intersection of the two
    set1 = set3 & set2 #reciprocal_friends
    reciprocal = list(set1)  #turns the set to a list
    return reciprocal #returns the list of mutual friends


# From Cookbook
def get_user_profile(twitter_api, screen_names=None, user_ids=None):
   
    # Must have either screen_name or user_id (logical xor)
    assert (screen_names != None) != (user_ids != None),     "Must have screen_names or user_ids, but not both"
    
    items_to_info = {}

    items = screen_names or user_ids
    
    while len(items) > 0:

        # Process 100 items at a time per the API specifications for /users/lookup.
        # See http://bit.ly/2Gcjfzr for details.
        
        items_str = ','.join([str(item) for item in items[:100]])
        items = items[100:]

        if screen_names:
            response = make_twitter_request(twitter_api.users.lookup, 
                                            screen_name=items_str)
        else: # user_ids
            response = make_twitter_request(twitter_api.users.lookup, 
                                            user_id=items_str)
    
        for user_info in response:
            if screen_names:
                items_to_info[user_info['screen_name']] = user_info
            else: # user_ids
                items_to_info[user_info['id']] = user_info

    return items_to_info

def popular(reciprocal): #Get the 5 most popular reciprocal friends
# Find most popular Reciprocal Friend with Most Followers
    reciprocal_followers = get_user_profile(twitter_api, user_ids=reciprocal)
    if len(reciprocal_followers)<=5:
        return reciprocal_followers
# Sort list of reciprocal friends
    dit = {id:reciprocal_followers[id]['followers_count'] for id in reciprocal_followers.keys()}

    sort = sorted(dit, key = dit.get, reverse = True)
        
    return sort[:5] #if len(dit) > 5 else sort[:]




# Use a crawler to get distance-2,d3,d4 friends and follow
def crawl_followers(twitter_api, screen_name, user_id=None): #from cookbook but modified

    G = nx.Graph() #graph name
    friends_ids, followers_ids = get_friends_followers_ids(twitter_api, screen_name=screen_name, friends_limit=5000, followers_limit=5000)
    # Find the reciprocal friends for first user
    response = popular(reciprocal_friends(friends_ids, followers_ids))
    print("Top 5 Reciprocal Friends is ", response)
    #Need the first id, then the next ids runs through the loop
    user_id = 165035772
    for i in response:
        G.add_edge(user_id, i)

    next_queue = response
    
    depth = 1 #root node
    collectedHundred = False
    max_depth = 1000
    # Find the reciprocal friends for the friends list
    while depth < max_depth and not collectedHundred:
        depth += 1
        (queue, next_queue) = (next_queue, []) #sets the queue as the top 5 friends and next_ queue as a empty list for the next group of top 5 friends for each user/node
        for id in queue: #repeats getting the top 5 for each user
            friends_ids, followers_ids = get_friends_followers_ids(twitter_api, user_id=id, friends_limit=5000, followers_limit=5000)
            response = popular(reciprocal_friends(friends_ids, followers_ids))
            print("Top 5 Reciprocal Friends for id:",id,"is ", response)
            for i in response:
                if (i not in next_queue and i not in G.nodes()): next_queue.append(i)
            for i in response:
                G.add_edge(id, i)
            # If the number of nodes exceeds 100, then break
            if (G.number_of_nodes() >= 100):
                collectedHundred = True
                break

    # print("Number of Nodes = {0}".format(nx.number_of_nodes(G)))
    # #Collect the nodes and draw the graph using subgraphs
    # connected_component_subgraphs = (G.subgraph(c) for c in nx.connected_components(G))
    # sg = max(connected_component_subgraphs, key=len)
    # print("The diameter is {0}".format(nx.diameter(sg)))
    # print("The average distance is {0}".format(nx.average_shortest_path_length(sg)))
    # # Draw the graph using matplot
    # nx.draw(G, node_color='cyan', with_labels=True)
    # plt.savefig("graph.png")
    # plt.show()


# Sample usage

#crawl_followers(twitter_api, screen_name='edmundyu1001')

# // KAREN PROJECT STARTS HERE \\ 

# filter keywords
# twitter_stream = twitter.TwitterStream(auth=twitter_api.auth)
# q = 'healthcare worker'
#q= EndLockdownsNow
#stream = twitter_stream.statuses.filter(track=q, language='en')

# q = 'NoMask'
# results = twitter_api.search.tweets(q=q,count=100, geocode='40.789100,-73.135000,1000mi')['statuses']


# for tweet in results:
# #     # Filter out RTs
#     if (not tweet['retweeted'] and 'RT @' not in tweet['text']):
#         try:
#             print()
#             print("//////////////////////////////////////////NEXT USER/////////////////////////////////")
#             print()

#             print (tweet['id'], tweet['created_at'], tweet['text'])
#         except:
#             pass
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
    
    print('Fetched {0} tweets'.format(len(tweets)), file=sys.stderr)
    
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

        print('Fetched {0} tweets'.format(len(tweets)),file=sys.stderr)
    
        page_num += 1
        
    print('Done fetching tweets', file=sys.stderr)

    return results[:max_results]

# q = "Karen"
# results = twitter_api.search.tweets(q=q,count=1000, geocode='34.1005166,-118.4146299,500mi')['statuses']
# tweets = [r['user'] for r in results]
# listOfNames = []

# def condition(dic):
#         namer = dic["name"]            
#         karen = "Karen"
#         if namer.find(karen) != -1 and (namer not in listOfNames):           
#             return True
            
            
# for i,t in enumerate(tweets):
#     try:
#         namer = t["name"] 
#         if (condition(t) and (namer not in listOfNames)):
#             listOfNames.append(namer)
#             karenTweets = harvest_user_timeline(twitter_api, screen_name=t["screen_name"], max_results=100)
#             print("//////////////////////////////////////////NEXT USER/////////////////////////////////")
#             print(t["screen_name"])           
#             for i, t in enumerate(karenTweets):
#                 if (('vaccine' or 'mask') in t['text']):
#                    # if (not t['retweeted'] and 'RT @' not in t['text']):
#                         try:
#                 #        print(i, "Timestamp: ", t['created_at'])
    
#                                 print("\n")
#                                 print(i, t['text']) # This 
#                         except:
#                                 pass
#     except:
#         pass
# Megan, Sophia, Emma, Emily, Martha, Natalie
from transformers import pipeline
# make sure to include "from transformers import pipeline" at top of program
userName= "Emma"
sys.stdout = open('emma_tweets.txt', 'w') #printing output to text file
sys.stdout.close() #This makes a clean text file each time its run so save the data if you need it later

#getting users with Karen in their twitter handle/name
results = twitter_api.users.search(q=userName, page=1)
results2 = twitter_api.users.search(q=userName, page=2)
results3 = twitter_api.users.search(q=userName, page=3)
results4 = twitter_api.users.search(q=userName, page=4)
results5 = twitter_api.users.search(q=userName, page=5)

#getting the Karen's names and locations
tweets1 = [(r['screen_name'], r['location']) for r in results]
tweets2 = [(r['screen_name'], r['location']) for r in results2]
tweets3 = [(r['screen_name'], r['location']) for r in results3]
tweets4 = [(r['screen_name'], r['location']) for r in results4]
tweets5 = [(r['screen_name'], r['location']) for r in results5]

#combining into one list
tweets1.extend(tweets2)
tweets1.extend(tweets3)
tweets1.extend(tweets4)
tweets1.extend(tweets5)
tweetCount = 0
posCount = 0
negCount = 0
confidenceScore = 0
sentimentanalyzer = pipeline("sentiment-analysis")

for (name,location) in tweets1:
            karenTweets = harvest_user_timeline(twitter_api, screen_name=name, max_results=100)
            sys.stdout = open('emma_tweets.txt', 'a')
            print("//////////////////////////////////////////NEXT USER/////////////////////////////////")
            print(name) 
            print(location)          
            for i, t in enumerate(karenTweets):
                #Do Megan Police tweets again
                #if ('police' in t['text'] or 'BLM' in t['text'] ):
                    # if (not t['retweeted'] and 'RT @' not in t['text']):
                try:  
                    tweetCount = tweetCount + 1
                    d = sentimentanalyzer(t['text'])
                    tweetLabel = d[0].get('label')
                    tweetScore = d[0].get('score')
                    if (tweetLabel=='POSITIVE'):
                        posCount = posCount + 1
                    else:
                        negCount = negCount + 1
                    confidenceScore = confidenceScore + float(tweetScore)
                    print("\n")                                
                    print(i, t['text'])
                    print(d)
                except:
                    pass
        

averageScore = confidenceScore / float(tweetCount)
positiveScore = (posCount / tweetCount) * 100
print(f"This program read {tweetCount} tweets")
print(f"Number of Positive Tweets is:{posCount}")
print(f"Number of Number of Tweets is:{negCount}")
print(f"{positiveScore}% of the tweets are positive")
print(f"The average confidence score is:{averageScore}")
sys.stdout.close()