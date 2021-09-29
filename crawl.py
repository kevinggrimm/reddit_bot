import os
import json
import logging
import sys
from datetime import datetime
from time import perf_counter, sleep

import requests
import praw

from config import config


# "https://www.reddit.com/prefs/apps"
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
for logger_name in ("praw", "prawcore"):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)

# Initialize reddit client
############################
client_id     = config.get('CLIENT_ID')
client_secret = config.get('CLIENT_SECRET')
username      = config.get('USERNAME')
password      = config.get('PASSWORD')
user_agent    = config.get('USER_AGENT')

reddit = praw.Reddit(
    client_id=client_id,
    client_secret=client_secret,
    username=username,
    password=password,
    user_agent=user_agent
)

# Load bot data
####################
keywords              = load_data('keywords')
redditors_contacted   = load_data('redditors')
subreddits            = load_data('subreddits')

# Load config data
####################
message_template    = config.get('message_template')
message_subject     = config.get('message_subject')
message_limit       = config.get('message_limit')
general_search_term = config.get('general_search_term')


def load_data(file_name, base_dir='data', ending='.txt'):
    with open(os.path.join(base_dir, f"{file_name}{ending}"), 'r') as f:
        data = set([l for l in f.read().split("\n")])
        return data


def write_data(data, file_name, base_dir='data', ending='.txt'):
    with open(os.path.join(base_dir, f"{file_name}{ending}"), 'w') as f:
        for line in data:
            f.write(line)
            f.write('\n')

def message_redditor(redditor, subreddit, subject=subject, message_template=message_template):
    try:
        message = message_template.replace('__SUBREDDIT__', subreddit)
        redditor.message(subject=subject, message=message)
    except Exception as e:
        print('Unable to message redditor: ', str(e))


def check_api_limits():
    requests_remaining = reddit.auth.limits.get('remaining')
    if requests_remaining > 0:
        return
    reset_datetime = datetime.fromtimestamp(reddit.auth.limits.get('reset_timestamp'))
    current_datetime = datetime.now()
    sleep_seconds = (reset_datetime - current_datetime).seconds
    sleep(sleep_seconds)


def message_submission_commenters(submission, subreddit, contacted_users, message_limit):
    messages_sent = 0

    title = submission.title.lower().split(' ')
    title_words = set([word for word in title])

    # Get comments if there is a keyword match
    #############################################
    if len(title_words.intersection(keywords)) >= 1:
        submission.comments.replace_more(limit=None)
        for comment in submission.comments.list():

            # Message user if not already contacted
            ########################################
            redditor = comment.author
            if redditor not in contacted_users:
                contacted_users.add(redditor.id)
                message_redditor(redditor, subreddit)
                messages_sent += 1

                # 
                ###########################
                if messages_sent == message_limit:
                    print('Hit message limit - exiting')
                    return messages_sent

SLEEP_TIME = 5
start_time = perf_counter()
messages_sent = 0
for submission in reddit.subreddit("all").search(general_search_term, limit=20):
    submission.comments.replace_more(limit=None)

    # Add subreddit to list if not found
    ####################################
    subreddit = submission.subreddit
    if subreddit not in subreddits:
        subreddits.add(subreddit)
    
    for comment in submission.comments.list():

        # Add redditor to list if not found
        ####################################
        redditor = comment.author
        redditor_id = redditor.id
        if redditor not in redditors_contacted:
            redditors_contacted.add(redditor_id)
            
            # Message redditor / increment counters / check rate limits
            ############################################################
            message_redditor(redditor, subreddit)
            check_api_limits()
            sleep(SLEEP_TIME)

            messages_sent += 1
            if messages_sent == message_limit:

                # TODO: Write sets to files

                end_time = perf_counter()
                total_runtime = end_time - start_time
                total_seconds = round(total_runtime, 2)
                total_minutes = round((end_time-start_time)/60, 2)

                print(f'Total runtime (seconds): {total_seconds}')
                print(f'Total runtime (minutes): {total_minutes}')
                sys.exit("Max number of messages sent - exiting program")


# TODO: Add subreddit-specific keyword matching
# for subreddit in subreddits:
#     print(subreddit)
#     sub = reddit.subreddit(subreddit)
#     for submission in sub.hot(limit=50):
#         title = submission.title.lower().split(' ')
#         title_words = set([word for word in title])
#         if len(title_words.intersection(keywords)) >= 1:
#             print(f'Match found in title: {title}')