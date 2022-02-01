from __future__ import print_function
import boto3
import json
import os
import logging
import xml.etree.ElementTree as ET

state_machine_arn = os.environ['STATE_MACHINE_ARN']
youtube_channel = os.environ['YOUTUBE_CHANNEL']

client = boto3.client('stepfunctions')


# Entrypoint for lambda funciton
def lambda_handler(event, context):

    log_level = str(os.environ.get('LOG_LEVEL')).upper()
    if log_level not in [
                        'DEBUG', 'INFO',
                        'WARNING', 'ERROR',
                        'CRITICAL'
                    ]:
      log_level = 'DEBUG'
    logging.getLogger().setLevel(log_level)

    logging.info(json.dumps(event))

    retVal = ''

    # Check if this is a subscription event and matches our channel
    if event["queryStringParameters"] and "hub.challenge" in event["queryStringParameters"] and event["queryStringParameters"]["hub.topic"].endswith(youtube_channel):
        retVal = event["queryStringParameters"]["hub.challenge"]
    else:

        root = ET.fromstring(event["body"])

        logging.info(root)


        for link in root.findall('./{http://www.w3.org/2005/Atom}entry/{http://www.w3.org/2005/Atom}link'):
            url = link.get("href")
            logging.info(url)

            smInput = {
              "youtubeUrl": url
            }

            response = client.start_execution(
                stateMachineArn=state_machine_arn,
                input=json.dumps(smInput)
            )
            logging.info(response)

        retVal = json.dumps({"success": True})


    logging.info(retVal)
    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "headers": {  },
        "body": retVal
    }
