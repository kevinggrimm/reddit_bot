import os
import json
import logging
import sys
from datetime import datetime
from time import perf_counter, sleep

import requests
import praw

from config import config


#####################################
def load_data(file_name, base_dir='data', ending='.txt'):
    with open(os.path.join(base_dir, f"{file_name}{ending}"), 'r') as f:
        data = set([l for l in f.read().split("\n")])
        return data

def write_data(data, file_name, base_dir='data', ending='.txt'):
    with open(os.path.join(base_dir, f"{file_name}{ending}"), 'w') as f:
        for line in data:
            f.write(line)
            f.write('\n')

def message_redditor(redditor, subreddit, message_subject=message_subject, message_template=message_template):
    try:
        print('Messaging redditor...')
        message = message_template.replace('__SUBREDDIT__', subreddit)
        redditor.message(subject=message_subject, message=message)
        print('Message sent to redditor')
        return True

    except Exception as e:       

        # Sleep for time specified in RATELIMIT error
        ############################################
        if 'RATELIMIT' in str(e):
            try:
                sleep_time = str(e).split('Take a break for ')[-1].split(' ')[0]
                print(f'Sleeping for {sleep_time} seconds....')
                sleep(int(sleep_time))
            except Exception as ex:
                print(f"Error trying to sleep: {str(ex)}")
        
        # General sleep for non whitelist error
        ################################################
        elif 'NOT_WHITELISTED_BY_USER_MESSAGE' in str(e):
            print(f'NOT WHITELISTED ERROR: {str(e)}')
            sleep(5)
        return False

def check_api_limits():
    """Sleeps for time specified in api limits (+ buffer) if no requests are remaining"""
    from time import sleep
    requests_remaining = reddit.auth.limits.get('remaining')
    print(f'API requests remaining: {requests_remaining}')
    reset_datetime = datetime.fromtimestamp(reddit.auth.limits.get('reset_timestamp'))
    current_datetime = datetime.now()
    seconds_until_reset = (reset_datetime - current_datetime).seconds
    print(f'Seconds until rate limit reset: {seconds_until_reset}')
    if requests_remaining > 0:
        return
    sleep(seconds_until_reset + 10)

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

MESSAGE_SLEEP_TIME  = config.get('message_sleep_time')
AUTHOR_SLEEP_TIME   = config.get('author_sleep_time')

############################################################################################################

# SCRAPER #1 - Pulling latest posts for general searches + updating subreddits // messaging users
    # TODO:
    # - Add different, independent keyword searches
    # - Keyword-specific messages
    # - Different processes
        # - Search by keyword (across all of reddit)
        # - Search by subreddits (predefined)
    # - Process replied messages
    # - Convert below processes into functions

############################################################################################################

start_time = perf_counter()
messages_sent = 0
errors_seen = 0

# TODO: Add subreddit, submission IDs for posts crawled
    # Can pick up process from subreddits/submissions not encountered in prior runs
while messages_sent < message_limit:
    print('Sending requests for search...')
    for submission in reddit.subreddit("all").search(general_search_term, limit=20):
        print('Changing comment replacement for submission...')
        submission.comments.replace_more(limit=None)

        # Add subreddit to list if not found
        ####################################
        print('Getting subreddit...')
        subreddit = submission.subreddit.display_name
        print(f'Subreddit: {subreddit}')
        if subreddit not in subreddits:
            print(f'Found new subreddit to crawl: {subreddit}')
            subreddits.add(subreddit)

        print(f'Crawling comments for subreddit : {subreddit}')
        for comment in submission.comments.list():

            # Add redditor to list if not found
            ####################################
            try:
                print('Fetching comment author...')
                redditor    = comment.author
                print(f'Comment author: {redditor}')
                print('Fetching author ID...')
                redditor_id = comment.author.id
                print(f'Author ID: {redditor_id}')
            except AttributeError:
                continue

            # Message redditor / increment counters / check rate limits
            ############################################################
            if redditor_id not in redditors_contacted:
                sleep(AUTHOR_SLEEP_TIME)
                print(f'New redditor to message: {redditor_id}')
                msg_status = message_redditor(redditor, subreddit)

                # Update contacted redditors, error count based on output
                ###########################################################
                if msg_status:
                    redditors_contacted.add(redditor_id)
                    messages_sent += 1
                    print('Checking rate limits...')
                else:
                    errors_seen += 1

                # Check API limits, sleep, increment messages
                #############################################
                check_api_limits()
                sleep(MESSAGE_SLEEP_TIME)
                if messages_sent >= message_limit:

                    # Write new redditors, subreddits to files
                    #############################################
                    write_data(redditors_contacted, 'redditors')
                    write_data(subreddits, 'subreddits')

                    end_time = perf_counter()
                    total_runtime = end_time - start_time
                    total_seconds = round(total_runtime, 2)
                    total_minutes = round((end_time-start_time)/60, 2)

                    print(f'Total runtime (seconds): {total_seconds}')
                    print(f'Total runtime (minutes): {total_minutes}')
                    print(f'Total errors seen: {errors_seen}')
                    sys.exit("Delivered max messages")


############################################################################################################
# SCRAPER #2 - Going through individual subs and pulling comments by keyword matches
    # TODO:
        # - refactor duplicate logic into functions for above, below crawls
        # - apply for other post types (e..g, hot, rising, gilded, top)
############################################################################################################

start_time = perf_counter()
messages_sent = 0
errors_seen = 0

while messages_sent < message_limit:
    for sub in subreddits:
        if sub != '':

            ####################
            #
            # HOT POSTS 
            #
            ####################
            for submission in reddit.subreddit(sub).hot(limit=50):
                title = submission.title.lower().split(' ')
                title_words = set([word for word in title])
                print(f'Title: {title}')
                if len(title_words.intersection(keywords)) > 1:
                    print(f'1+ keyword matches found in title: {title_words}')
                    print('Changing comment replacement for submission...')
                    submission.comments.replace_more(limit=None)

                    # Add subreddit to list if not found
                    ####################################
                    subreddit = sub
                    print(f'Crawling comments for subreddit : {subreddit}')
                    for comment in submission.comments.list():

                        # Add redditor to list if not found
                        ####################################
                        try:
                            print('Fetching comment author...')
                            redditor    = comment.author
                            print(f'Comment author: {redditor}')
                            print('Fetching author ID...')
                            redditor_id = comment.author.id
                            print(f'Author ID: {redditor_id}')
                        except AttributeError:
                            continue

                        # Message redditor / increment counters / check rate limits
                        ############################################################
                        if redditor_id not in redditors_contacted:
                            sleep(AUTHOR_SLEEP_TIME)
                            print(f'New redditor to message: {redditor_id}')
                            msg_status = message_redditor(redditor, subreddit)
                            if msg_status:
                                redditors_contacted.add(redditor_id)
                                messages_sent += 1
                                print(f'Redditors Contacted: {len(redditors_contacted)}')
                            else:
                                errors_seen += 1
                                print(f'Errors seen: {errors_seen}')
                            print('Checking rate limits...')
                            check_api_limits()
                            sleep(MESSAGE_SLEEP_TIME)

                            if messages_sent >= message_limit:
                                # Write new redditors, subreddits to files
                                #############################################
                                write_data(redditors_contacted, 'redditors')
                                write_data(subreddits, 'subreddits')

                                end_time = perf_counter()
                                total_runtime = end_time - start_time
                                total_seconds = round(total_runtime, 2)
                                total_minutes = round((end_time-start_time)/60, 2)

                                print(f'Total runtime (seconds): {total_seconds}')
                                print(f'Total runtime (minutes): {total_minutes}')
                                print(f'Total errors seen: {errors_seen}')
                                sys.exit("Delivered max messages")
 
# TODO: Add subreddit-specific keyword matching
# for subreddit in subreddits:
#     print(subreddit)
#     sub = reddit.subreddit(subreddit)
#     for submission in sub.hot(limit=50):
#         title = submission.title.lower().split(' ')
#         title_words = set([word for word in title])
#         if len(title_words.intersection(keywords)) >= 1:
#             print(f'Match found in title: {title}')