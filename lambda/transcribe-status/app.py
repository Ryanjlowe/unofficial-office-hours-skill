from __future__ import print_function
import boto3
from botocore.client import Config
import datetime
import logging
import os

client = boto3.client('transcribe')

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

    transcribeJob = event['transcribeJob']

    # Call the AWS SDK to get the status of the transcription job
    response = client.get_transcription_job(TranscriptionJobName=transcribeJob)
    logging.info(response)

    # Pull the status
    status = response['TranscriptionJob']['TranscriptionJobStatus']

    retval = {
        "mediaS3Location": event['mediaS3Location'],
        "metadata": event["metadata"],
        "content_type": event['content_type'],
        "transcribeJob": event['transcribeJob'],
        "status": status
    }

    # If the status is completed, return the transcription file url. This will be a signed url
    # that will provide the full details on the transcription
    if status == 'COMPLETED':
        retval["transcriptionUrl"] = response['TranscriptionJob']['Transcript']['TranscriptFileUri']

    logging.debug(retval)
    return retval
