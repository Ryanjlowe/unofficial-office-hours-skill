import os
from urllib.request import urlopen
import json
import os
import string
import random
import logging
import boto3
from botocore.client import Config

# Create SDK clients for comprehend and S3
client = boto3.client('comprehend')
s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3')

bucket = os.environ['BUCKET_NAME']

entityTypes = ['COMMERCIAL_ITEM', 'EVENT', 'LOCATION', 'ORGANIZATION', 'TITLE', 'PERSON']

# Creates a random string for file name
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

# Main entry point for the lambda function
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

    # Pull the bucket name from the environment variable set in the cloudformation stack

    s3val = []
    paragraphs = []

    # Pull the signed URL for the payload of the transcription job
    transcriptionUrl = event['transcriptionUrl']
    output_key = 'transcribe_results/' + transcriptionUrl.split("/")[-1]

    # START SKIP
    # response = s3_client.get_object(Bucket=event["vocabularyInfo"]['mapping']['bucket'],
    #                                 Key=event["vocabularyInfo"]['mapping']['key'])
    # file_content = response['Body'].read().decode('utf-8')
    #
    # mapping = json.loads(file_content)
    # logging.debug("Received mapping: ")
    # logging.debug(mapping)
    # END SKIP

    obj = s3_resource.Object(bucket, output_key)
    jsonstr = obj.get()['Body'].read().decode('utf-8')
    j = json.loads(jsonstr)

    # Here is the JSON returned by the Amazon Transcription SDK
    # {
    #  "jobName":"JobName",
    #  "accountId":"Your AWS Account Id",
    #  "results":{
    #    "transcripts":[
    #        {
    #            "transcript":"ah ... this is the text of the transcript"
    #        }
    #    ],
    #    "items":[
    #        {
    #            "start_time":"0.630",
    #            "end_time":"5.620",
    #            "alternatives": [
    #                {
    #                    "confidence":"0.7417",
    #                    "content":"ah"
    #                }
    #            ],
    #            "type":"pronunciation"
    #        }
    #     ]
    #  }

    # Pull the items from the transcription. Each word will be its own item with a start and endtime
    items = j["results"]["items"]

    # We would like to determine the key phrases in the transcript to so we can search on common phrases
    # rather than a single word at a time. In order to maintain the relationship between the time
    # the text is spoken and search on it, we need to pass each phrase individually along with its
    # timestamp so we retain that relationship. We will use comprehend to extract the ckey phrases from
    # the text.

    contents = ""
    timedata = []

    prevEndTime = -1
    paragraphGap = 1.5
    prevStartTime = -1
    newParagraph = False
    prevSpeaker = 'spk_0'

    hasSpeakerLabels = False
    speakerMapping = []

    # Create a mapping of the transitions from one speaker to another
    if 'speaker_labels' in j['results']:
        hasSpeakerLabels = True
        for i in range(len(j['results']['speaker_labels']['segments'])):
            speakerLabel = j['results']['speaker_labels']['segments'][i]
            speakerMapping.append(
                {
                    "speakerLabel": speakerLabel['speaker_label'],
                    "endTime": float(speakerLabel['end_time'])
                })

    speakerIndex = 0

    # Repeat the loop for each item (word and punctuation)
    # The transcription will be broken out into a number of sections that are referred to
    # below as paragraphs. The paragraph is the unit text that is stored in the
    # elasticsearch index. It is broken out by punctionation, speaker changes, a long pause
    # in the audio, or overall length
    for i in range(len(items)):
        reason = ""

        # If the transcription detected the end of a sentence, we'll
        if items[i]['type'] == 'punctuation':
            if items[i]["alternatives"][0]["content"] == '.':
                newParagraph = True

            # Always assume the first guess is right.
            contents += items[i]["alternatives"][0]["content"]

        # Add the start time to the string -> timedata
        if 'start_time' in items[i]:
            speakerLabel = 'spk_0'

            if prevStartTime == -1:
                prevStartTime = float(items[i]["start_time"])

            # gap refers to the amount of time between spoken words
            gap = float(items[i]["start_time"]) - prevEndTime

            if hasSpeakerLabels:
                while speakerIndex < (len(speakerMapping) - 1) and speakerMapping[speakerIndex + 1]['endTime'] < float(
                        items[i]["start_time"]):
                    speakerIndex += 1

                speakerLabel = speakerMapping[speakerIndex]['speakerLabel']

            # Change paragraphs if the speaker changes
            if speakerLabel != prevSpeaker:
                newParagraph = True
                reason = "Speaker Change from " + prevSpeaker + " to " + speakerLabel
            # the gap exceeds a preset threshold
            elif gap > paragraphGap:
                newParagraph = True
                reason = "Time gap"
            # There are over 4900 words (The limit for comprehend is 5000)
            elif len(contents) > 4900:
                newParagraph = True
                reason = "Long paragraph"
            else:
                newParagraph = False

            if prevEndTime != -1 and newParagraph:

                # append the block of text to the array. Call comprehend to get
                # the keyword tags for this block of text
                s3val.append({
                    "startTime": prevStartTime,
                    "endTime": prevEndTime,
                    "text": contents,
                    "gap": gap,
                    "tags": run_comprehend(contents),
                    "key_phrases": run_comprehend_key_phrases(contents),
                    "reason": reason,
                    "speaker": prevSpeaker,
                    "len": len(contents)
                })
                # Reset the contents and the time mapping
                logging.info('paragraph:')
                logging.info(contents)

                contents = ""
                timedata = []
                prevEndTime = -1
                prevStartTime = -1
                newParagraph = False
            else:
                prevEndTime = float(items[i]["end_time"])

            prevSpeaker = speakerLabel

            # If the contents is not empty, prepend a space
            if contents != "":
                contents += " "

            # Always assume the first guess is right.
            word = items[i]["alternatives"][0]["content"]

            # START SKIP
            # Map the custom words back to their original text
            # for key in mapping:
            #     val = mapping[key]
            #     word = word.replace(key, val)
            # END SKIP

            contents += word

    # Run Comprehend on the remaining text
    # run_comprehend(contents, timedata, s3val)

    s3val.append({
        "startTime": prevStartTime,
        "endTime": prevEndTime,
        "text": contents,
        "tags": run_comprehend(contents),
        "key_phrases": run_comprehend_key_phrases(contents),
        "speaker": prevSpeaker
    })

    # Create a payload for the output of the transcribe and comprehend API calls. There's a limit on the
    # amount of data stored in a step function payload, so we will use S3 to store the payload instead.
    # This can get to be pretty big.
    key = 'comprehend_output/keywords/' + id_generator() + '.json'
    # store s3val to s3
    response = s3_client.put_object(Body=json.dumps(s3val, indent=2), Bucket=bucket, Key=key)

    logging.debug("S3 Value: ")
    logging.debug(s3val)

    # Return the bucket and key of the transcription / comprehend result.

    retVal = {
        "mediaS3Location": event['mediaS3Location'],
        "metadata": event["metadata"],
        "content_type": event['content_type'],
        "transcribeJob": event['transcribeJob'],
        "transcriptionUrl": event['transcriptionUrl'],
        "bucket": bucket,
        "key": key
    }
    logging.debug(retVal)
    return retVal


# Run comprehend and extract the key phrases from the podcast.
def run_comprehend(text):
    response = client.detect_entities(Text=text, LanguageCode='en')
    keywords = []
    for i in range(len(response["Entities"])):
        entity = response["Entities"][i]
        if entity['Type'] in entityTypes:
            keywords.append(entity["Text"])

    return keywords

# Run comprehend and extract the key phrases from the podcast.
def run_comprehend_key_phrases(text):
    response = client.detect_key_phrases(Text=text, LanguageCode='en')
    return response["KeyPhrases"]



# uses the offset in the string and the timedata mapping to convert the string index to a time value from
# the audio file.
def convertPositionToTime(offset, timedata):
    timeposition = ""
    for i in range(len(timedata)):
        if int(timedata[i]["position"]) <= int(offset):
            timeposition = timedata[i]["startTime"]

    return timeposition
