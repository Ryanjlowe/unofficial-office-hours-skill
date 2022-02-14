from __future__ import print_function
import boto3
from botocore.client import Config
import datetime
import logging
import os
import json
import urllib.request
import urllib.parse

youtube_channel = os.environ['YOUTUBE_CHANNEL']
# callback_url = os.environ['CALLBACK_URL']
secret = os.environ['SECRET']

# The entry point for the lambda function
def lambda_handler(event, context):

    log_level = str(os.environ.get('LOG_LEVEL')).upper()
    if log_level not in [
                        'DEBUG', 'INFO',
                        'WARNING', 'ERROR',
                        'CRITICAL'
                    ]:
      log_level = 'INFO'
    logging.getLogger().setLevel(log_level)

    logging.debug(event)

    callback_url = event['callback_url']

    # state_machine_arn = event["StateMachineARN"]


    safe_callback = safe_string = urllib.parse.quote_plus(callback_url)
    safe_topic = safe_string = urllib.parse.quote_plus(f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={youtube_channel}")

    url = f"https://pubsubhubbub.appspot.com/subscribe?hub.callback={safe_callback}&hub.mode=subscribe&hub.topic={safe_topic}&hub.secret={secret}"

    logging.info(url)

    # Re-subscribe
    contents = urllib.request.urlopen(url).read()
    logging.info(contents)


    # # Get Status
    # url2 = f"https://pubsubhubbub.appspot.com/subscription-details?hub.callback={safe_callback}&hub.topic={safe_topic}&hub.secret={secret}"
    # logging.info(url2)

    # contents = urllib.request.urlopen(url2).read()
    # logging.info(contents)
    

    # smInput = {
    #     "secondsWait": 432000
    # }

    # response = client.start_execution(
    #     stateMachineArn=state_machine_arn,
    #     input=json.dumps(smInput)
    # )
    # logging.info(response)


    return True
