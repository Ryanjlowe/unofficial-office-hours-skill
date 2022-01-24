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


bucket = os.environ['BUCKET_NAME']
role = os.environ['MEDIACONVERT_ROLE']
template_name = os.environ['MEDIACONVERT_TEMP_NAME']

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

    logging.info(event)

    file = "s3://" + event['mediaS3Location']['bucket'] + "/" + event['mediaS3Location']['key']

    endpoint_client = boto3.client('mediaconvert')

    endpoint_response = endpoint_client.describe_endpoints()
    logging.debug(endpoint_response)
    endpoint = endpoint_response["Endpoints"][0]["Url"]

    client = boto3.client('mediaconvert', endpoint_url=endpoint)

    response = client.create_job(
        Role=role,
        JobTemplate=template_name,
        Settings={
            "Inputs":[{
                "FileInput":file
            }]
        }
    )

    logging.debug(response)

    retVal = {
        "mediaS3Location": {
            "bucket": event['mediaS3Location']['bucket'],
            "key": event['mediaS3Location']['key']
        },
        "mediaconvertJobId": response["Job"]["Id"]
    }
    logging.info(retVal)
    return retVal
