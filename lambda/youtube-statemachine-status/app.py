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


    response = client.describe_execution(
        executionArn=event["ExecutionArn"]
    )
    logging.info(response)


    retVal = {
        "Urls": event["Urls"],
        "Index": event["Index"],
        "Length": event["Length"],
        "ExecutionArn": event["ExecutionArn"],
        "ExecutionStatus": response["status"]
    }

    logging.info(retVal)
    return retVal
