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

role = os.environ['MEDIACONVERT_ROLE']

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

    videoFile = "s3://" + event['mediaS3Location']['bucket'] + "/" + event['mediaS3Location']['videoKey']
    audioFile = "s3://" + event['mediaS3Location']['bucket'] + "/" + event['mediaS3Location']['audioKey']
    destination = "s3://" + event['mediaS3Location']['bucket'] + "/processed/"

    endpoint_client = boto3.client('mediaconvert')

    endpoint_response = endpoint_client.describe_endpoints()
    logging.debug(endpoint_response)
    endpoint = endpoint_response["Endpoints"][0]["Url"]

    client = boto3.client('mediaconvert', endpoint_url=endpoint)

    response = client.create_job(
        Role=role,
        Settings={
            "TimecodeConfig": {
              "Source": "ZEROBASED"
            },
            "OutputGroups": [
              {
                "CustomName": "Group",
                "Name": "File Group",
                "Outputs": [
                  {
                    "ContainerSettings": {
                      "Container": "MP4",
                      "Mp4Settings": {}
                    },
                    "VideoDescription": {
                      "CodecSettings": {
                        "Codec": "H_264",
                        "H264Settings": {
                          "MaxBitrate": 5000000,
                          "RateControlMode": "QVBR",
                          "SceneChangeDetect": "TRANSITION_DETECTION"
                        }
                      }
                    },
                    "AudioDescriptions": [
                      {
                        "AudioSourceName": "Audio Selector 1",
                        "CodecSettings": {
                          "Codec": "AAC",
                          "AacSettings": {
                            "Bitrate": 96000,
                            "CodingMode": "CODING_MODE_2_0",
                            "SampleRate": 48000
                          }
                        }
                      }
                    ]
                  }
                ],
                "OutputGroupSettings": {
                  "Type": "FILE_GROUP_SETTINGS",
                  "FileGroupSettings": {
                    "Destination": destination
                  }
                }
              }
            ],
            "Inputs": [
              {
                "AudioSelectors": {
                  "Audio Selector 1": {
                    "DefaultSelection": "DEFAULT",
                    "ExternalAudioFileInput": audioFile
                  }
                },
                "VideoSelector": {},
                "TimecodeSource": "ZEROBASED",
                "FileInput": videoFile
              }
            ]
          }
    )

    logging.debug(response)

    retVal = {
        "mediaS3Location": {
            "bucket": event['mediaS3Location']['bucket'],
            "videoKey": event['mediaS3Location']['videoKey'],
            "audioKey": event['mediaS3Location']['audioKey'],
        },
        "mediaconvertJobId": response["Job"]["Id"],
        "mediaconvertEndpoint": endpoint
    }
    logging.info(retVal)
    return retVal
