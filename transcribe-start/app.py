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


class ThrottlingException(Exception):
    pass


CONTENT_TYPE_TO_MEDIA_FORMAT = {
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/flac": "flac",
    "audio/mp4a-latm": "mp4"}


class InvalidInputError(ValueError):
    pass


# Custom encoder for datetime objects
class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return int(mktime(obj.timetuple()))
        return json.JSONEncoder.default(self, obj)


# limit the number of retries submitted by boto3 because Step Functions will handle the exponential retries more efficiently
config = Config(
    retries=dict(
        max_attempts=2
    )
)

client = boto3.client('transcribe', config=config)

output_bucket = os.environ['BUCKET_NAME']

# Creates a random string for file name
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

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

    logging.debug(event)

    session = boto3.session.Session()
    region = session.region_name

    # Default to unsuccessful
    isSuccessful = "FALSE"

    # Create a random name for the transcription job
    jobname = id_generator()

    # Extract the bucket and key from the downloadPodcast lambda function
    bucket = event['mediaS3Location']['bucket']
    key = event['mediaS3Location']['key']

    content_type = event['content_type']
    if content_type not in CONTENT_TYPE_TO_MEDIA_FORMAT:
        raise InvalidInputError(content_type + " is not supported audio type.")
    media_type = CONTENT_TYPE_TO_MEDIA_FORMAT[content_type]
    logging.info("media type: " + content_type)

    # Assemble the url for the object for transcribe. It must be an s3 url in the region
    url = "https://s3-" + region + ".amazonaws.com/" + bucket + "/" + key

    try:
        settings = {
            'VocabularyName': os.environ.get('TRANSCRIBE_VOCAB_NAME'),
            'ShowSpeakerLabels': False
        }

        # Call the AWS SDK to initiate the transcription job.
        response = client.start_transcription_job(
            TranscriptionJobName=jobname,
            LanguageCode='en-US',
            OutputBucketName=output_bucket,
            OutputKey='transcribe_results/',
            Settings=settings,
            MediaFormat=media_type,
            Media={
                'MediaFileUri': url
            }
        )
        logging.info(response)
        isSuccessful = "TRUE"
    except client.exceptions.BadRequestException as e:
        # There is a limit to how many transcribe jobs can run concurrently. If you hit this limit,
        # return unsuccessful and the step function will retry.
        logging.error(str(e))
        raise ThrottlingException(e)
    except client.exceptions.LimitExceededException as e:
        # There is a limit to how many transcribe jobs can run concurrently. If you hit this limit,
        # return unsuccessful and the step function will retry.
        logging.error(str(e))
        raise ThrottlingException(e)
    except client.exceptions.ClientError as e:
        # Return the transcription job and the success code
        # There is a limit to how many transcribe jobs can run concurrently. If you hit this limit,
        # return unsuccessful and the step function will retry.
        logging.error(str(e))
        raise ThrottlingException(e)

    retVal = {
        "mediaS3Location": {
            "bucket": event['mediaS3Location']['bucket'],
            "key": event['mediaS3Location']['key']
        },
        "content_type": event['content_type'],
        "success": isSuccessful,
        "transcribeJob": jobname
    }
    logging.debug(retVal)
    return retVal
