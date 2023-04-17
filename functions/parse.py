# For understanding please visit https://github.com/twitterdev/Twitter-API-v2-sample-code

from distutils.log import Log
from logging import Logger, raiseExceptions
import requests
import time
import json
from dotenv import dotenv_values
from functions.settings import RETWEET_URL, OWNER_ID, HASHTAGS
from functions.errors import *

config = dotenv_values("functions/.env")
bearer_token=config["BEARER_TOKEN"]
retweet_id = RETWEET_URL.split("/")[-1]


def create_id_url(username: str):
    '''
    Creates url for request to get user id from username given for bot by user
    '''
    # Specify the usernames that you want to lookup below
    # You can enter up to 100 comma-separated values.
    usernames = "usernames={}".format(username)
    user_fields = "user.fields=id"
    # User fields are adjustable, options include:
    # created_at, description, entities, id, location, name,
    # pinned_tweet_id, profile_image_url, protected,
    # public_metrics, url, username, verified, and withheld
    url = "https://api.twitter.com/2/users/by?{}&{}".format(usernames, user_fields)
    return url



def create_url(user_id: int, since_id: str):
    '''
    Create url for request to get list of tweets
    '''
    # Replace with user ID below
    return f"https://api.twitter.com/2/users/{user_id}/tweets/?since_id={since_id}&max_results=100"

def add_pagination_token(url: str, pagination_token:str):
    return url + f"&pagination_token={pagination_token}"

def id_connect_to_endpoint(url):
    '''
    Make request from create_id_url (request to get user id from username)
    '''
    response = requests.request("GET", url, auth=bearer_oauth,)\
    
    if response.status_code != 200:
        raise RateLimitError
    
    r = response.json()
    
    errors = r.get("errors")
    if errors != None:
        for err in errors:
            if err["title"] == "Not Found Error":
                raise UserNotFoundError
 
    return response.json()


def get_params():
    # Tweet fields are adjustable.
    # Options include:
    # attachments, author_id, context_annotations,
    # conversation_id, created_at, entities, geo, id,
    # in_reply_to_user_id, lang, non_public_metrics, organic_metrics,
    # possibly_sensitive, promoted_metrics, public_metrics, referenced_tweets,
    # source, text, and withheld
    return {"tweet.fields": "referenced_tweets"}


def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """

    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2UserTweetsPython"
    return r


def connect_to_endpoint(url, params):
    '''
    Make request from create_url
    '''
    response = requests.request("GET", url, auth=bearer_oauth, params=params)
    
    if response.status_code != 200:
        raise RateLimitError
    return response.json()

def if_needed_tweet(ref_tweets: list, id: str):
    '''
    Takes referenced_tweets param and checks for retweet of ours post
    '''
    if len(ref_tweets) > 0:
        tweet = ref_tweets[0]
        if (tweet["type"] == "quoted") or (tweet["type"] == "retweeted"):
            if tweet["id"] == id:
                return True
    return False

def search_for_tweet(url: str, params: dict):
    '''
    Goes through tweets and searches for retweet & post with hashtags
    '''
    require = {
        "retweet": False,
        "post": False
    }

    json_response = connect_to_endpoint(url, params)

    r = json.dumps(json_response, indent=4, sort_keys=True)
    dict_response = json.loads(r)

    meta = dict_response.get("meta")
    if meta != None:
        if meta["result_count"] == 0:
            raise PostNotFoundError

    tweets = dict_response.get("data")
    if tweets == None:
        raise PostNotFoundError

    for i in range(10):
        # print(dict_response)
        for tweet in dict_response["data"]:
            if not require["retweet"]:
                if tweet.get("referenced_tweets") != None: 
                    if if_needed_tweet(tweet["referenced_tweets"], retweet_id):
                        require["retweet"] = True
                        if require["post"]:
                            return
            if not require["post"]:
                text = tweet.get("text")
                if text:
                    if (HASHTAGS[0] in text.lower()) and (HASHTAGS[1] in text.lower()):
                        require["post"] = True
                        if require["retweet"]:
                            return
        if "next_token" in dict_response["meta"].keys():
            new_url = add_pagination_token(url, dict_response["meta"]["next_token"])
            json_response = connect_to_endpoint(new_url, params)

            r = json.dumps(json_response, indent=4, sort_keys=True)
            dict_response = json.loads(r)
        else:
            if not require["post"]:
                raise PostNotFoundError
            raise RetweetNotFoundError
    if not require["post"]:
        raise PostNotFoundError
    raise RetweetNotFoundError

def check_follow_from_json(user_id: int):
    with open("followers.json") as f:
        ids = f.read().strip()
    return user_id in json.loads(ids)["data"]

def check_if_user_follows(user_id: int) -> bool:
    '''
    Checks if user follows and raises an excemption if no
    '''
    url = "https://api.twitter.com/2/users/{}/following".format(user_id)

    def get_params():
        return {"max_results": "1000"}
    params = get_params()

    json_response = connect_to_endpoint(url, params=params)
    r = json.dumps(json_response, indent=4, sort_keys=True)
    dict_response = json.loads(r)

    data = dict_response.get("data")
    if not data:
        raise DoesNotFollowError

    for i in range(10):
        for user in dict_response["data"]:
            if user["id"] == OWNER_ID:
                return
        if "next_token" in dict_response["meta"].keys():
            new_url = add_pagination_token(url, dict_response["meta"]["next_token"])
            json_response = connect_to_endpoint(new_url, params=params)

            r = json.dumps(json_response, indent=4, sort_keys=True)
            dict_response = json.loads(r)
        else:
            raise DoesNotFollowError
    raise DoesNotFollowError

def check_if_twitter_fits(twi, name: str, logger: Logger):
    logger.info(name)

    id_url = create_id_url(twi)

    logger.info(f"{name}, fetching user_id")
    json_response = id_connect_to_endpoint(id_url)
    resp = json.dumps(json_response, indent=4, sort_keys=True)

    user_id = json.loads(resp)["data"][0]["id"]
    
    logger.info(f"{name}, checking if user follows account")

    # in case of errors because file is opened by several threads
    try:
        fol_from_json = check_follow_from_json(user_id)
    except:
        time.sleep(1)
        try:
            fol_from_json = check_follow_from_json(user_id)
        except:
            fol_from_json = False

    if not fol_from_json:
        check_if_user_follows(user_id)

    url = create_url(int(user_id), since_id=retweet_id)
    params = get_params()

    logger.info(f"{name}, iterating through tweets")
    return search_for_tweet(url=url, params=params)