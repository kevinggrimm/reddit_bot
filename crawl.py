import os
import json

import requests
import praw

# "https://www.reddit.com/prefs/apps"

def get_contacted_users():
    contacted_users = set()
    for msg in reddit.inbox.messages():
        if msg.dest.id not in contacted_users:
            contacted_users.add(msg.dest.id)
            
    return contacted_users

def message_redditor(redditor, subreddit, subject=subject, message_template=message_template):
    try:
        message = message_template.replace('__SUBREDDIT', subreddit)
        redditor.message(subject=subject, message=message)
    except Exception as e:
        print('Unable to message author: ', str(e))

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
            redditor = c.author
            if redditor not in contacted_users:
                contacted_users.add(redditor.id)
                message_redditor(redditor, subreddit)
                messages_sent += 1

                # 
                ###########################
                if messages_sent == message_limit:
                    print('Hit message limit - exiting')
                    return messages_sent



secret                  = os.getenv('REDDIT_SECRET', None)
username                = os.getenv('REDDIT_USERNAME', None)
password                = os.getenv('REDDIT_PASSWORD', None)
user_agent              = os.getenv('REDDIT_USER_AGENT', None)
personal_use_script     = os.getenv('REDDIT_PERSONAL_SCRIPT', None)

reddit = praw.Reddit(
    client_id=personal_use_script,
    client_secret=secret,
    user_agent=user_agent,
    username=username,
    password=password
)

# Keywords, post categories, subreddits to include in search
##############################################################
keywords = set([
    'SEC', 'insider', 'insiders', 'transactions', 'trades', 'benchmark', 'performance',
    'openinsider', 'data', 'analysis', 'benchmark', 'trade', 'transaction', 'stock',
    'purchase', 'purchases', 'industry', 'market', 'stocks', 'form', 'strategy',
    'ownership'
])

post_categories = ['hot', 'rising', 'top', 'gilded']

subreddits = [
    'investing',
    'Superstonk',
    'FluentInFinance',
    'StockMarket',
    'wallstreetbets',
    'options',
    'stocks',
    'GME',
    'ASX_Bets',
    'amcstock',
    'market_sentiment'
]

# Message template, subject
#############################

subject='Form 4 / SEC Filings Project'

message_template = """
Hey, I saw your comment in r/__SUBREDDIT__ and wanted to reach out about a related project that I am building to view Form 4 filings. The app will have features like real-time updates, email alerts, views by insiders/ title, companies, industry group/sub-group, and 15+ years of filings.

Wondering if you would be interested in receiving progress updates via email or Reddit (I am targeting a beta release by EOY). Would also be great to get a sense of what other SEC data you would like to access and pain points you might have experienced.

Anyways, figured I would run it by you in case it is of any interest.
"""

# Main script

contacted_users = get_contacted_users()
posts_crawled = set()
message_limit = 100


for subreddit in subreddits:
    print(subreddit)
    sub = reddit.subreddit(subreddit)
    
    # Hot posts
    ##############
    for submission in sub.hot(limit=1):
        messages_sent = message_submission_commenters(submission, subreddit, contacted_users, message_limit)
        message_limit -= messages_sent        
        break


## TODO: Review + Incorporate into main script
# users_contacted = 0
# message_limit = 100

# for subreddit in subreddits:
#     print(subreddit)
#     sub = reddit.subreddit(subreddit)
#     for submission in sub.hot(limit=50):
#         title = submission.title.lower().split(' ')
#         title_words = set([word for word in title])
#         if len(title_words.intersection(keywords)) >= 1:
#             print(f'Match found in title: {title}')
            

    
#     users_contacted += 1
#     if users_contacted == message_limit:
#         print(f'Reached message limit of {message_limit} - exiting')

# submission = reddit.submission(url="https://www.reddit.com/r/investing/comments/puhzwr/should_you_follow_insider_transactions_i_analyzed/")

