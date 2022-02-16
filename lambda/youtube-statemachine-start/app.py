from __future__ import print_function
import boto3
import json
import os
import logging

state_machine_arn = os.environ['STATE_MACHINE_ARN']

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

    url = event["Urls"][event["Index"]]

    smInput = {
        "youtubeUrl": url
    }

    response = client.start_execution(
        stateMachineArn=state_machine_arn,
        input=json.dumps(smInput)
    )
    logging.info(response)

    retVal = {
        "Urls": event["Urls"],
        "Index": event["Index"] + 1,
        "Length": event["Length"],
        "ExecutionArn": response["executionArn"]
    }

    logging.info(retVal)
    return retVal
