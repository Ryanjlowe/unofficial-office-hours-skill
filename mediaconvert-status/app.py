from __future__ import print_function
import boto3
import json
import datetime
from time import mktime
import os
import logging
import random
import string
from botocore.config import Config


# Entrypoint for lambda funciton
def lambda_handler(event, context):

    log_level = str(os.environ.get('LOG_LEVEL')).upper()
    if log_level not in [
                        'DEBUG', 'INFO',
                        'WARNING', 'ERROR',
                        'CRITICAL'
                    ]:
      log_level = 'INFO'
    logging.getLogger().setLevel(log_level)

    logging.info(event)

    endpoint = event["mediaconvertEndpoint"]

    client = boto3.client('mediaconvert', endpoint_url=endpoint)

    response = client.get_job(
        Id=event["mediaconvertJobId"]
    )

    logging.debug(response)

    output_prefix = "processed/" + event['mediaS3Location']['videoKey'].split("/")[1]

    retVal = {
        "mediaS3Location": {
            "bucket": event['mediaS3Location']['bucket'],
            "videoKey": event['mediaS3Location']['videoKey'],
            "audioKey": event['mediaS3Location']['audioKey'],
        },
        "mediaconvertEndpoint": event["mediaconvertEndpoint"],
        "mediaconvertJobId": event["mediaconvertJobId"],
        "status": response["Job"]["Status"],
        "output_prefix": output_prefix,
        "content_type": "mp4"
    }
    logging.info(retVal)
    return retVal
