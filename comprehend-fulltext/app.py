from __future__ import print_function  # Python 2/3 compatibility

import boto3
import botocore
import os
import logging
import time
import json
from urllib.request import urlopen
import string
import random

# Parameters

comprehend = boto3.client('comprehend')

commonDict = {'i': 'I'}

ENTITY_CONFIDENCE_THRESHOLD = 0.5

KEY_PHRASES_CONFIDENCE_THRESHOLD = 0.7

s3_client = boto3.client("s3")
s3_resource = boto3.resource('s3')

# Pull the bucket name from the environment variable set in the cloudformation stack
bucket = os.environ['BUCKET_NAME']

class InvalidInputError(ValueError):
    pass

# Creates a random string for file name
def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def find_duplicate_person(people):
    duplicates = []
    for i, person in enumerate(people):
        for j in range(i + 1, len(people)):
            if person in people[j]:
                if person not in duplicates:
                    duplicates.append(person)
                logger.info("found " + person + " in " + people[j])
            if people[j] in person:
                logger.info("found " + people[j] + " in " + person)
                if people[j] not in duplicates:
                    duplicates.append(people[j])
    return duplicates


def process_transcript(transcription_url, vocabulary_info):
    custom_vocabs = None
    # START SKIP
    # if "mapping" in vocabulary_info:
    #     try:
    #         vocab_mapping_bucket = vocabulary_info['mapping']['bucket']
    #         key = vocabulary_info['mapping']['key']
    #         obj = s3_client.get_object(Bucket=vocab_mapping_bucket, Key=key)
    #         custom_vocabs = json.loads(obj['Body'].read())
    #         logging.info("key:" + key)
    #         logging.info("using custom vocab mapping: \n" + json.dumps(custom_vocabs, indent=2))
    #     except botocore.exceptions.ClientError as e:
    #         if e.response['Error']['Code'] == "404":
    #             raise InvalidInputError("The S3 file for custom vocab list does not exist.")
    #         else:
    #             raise
    # END SKIP

    # job_status_response = transcribe_client.get_transcription_job(TranscriptionJobName=transcribe_job_id)

    output_key = 'transcribe_results/' + transcription_url.split("/")[-1]

    obj = s3_resource.Object(bucket, output_key)
    jsonstr = obj.get()['Body'].read().decode('utf-8')
    json_data = json.loads(jsonstr)

    logging.debug(json_data)
    results = json_data['results']
    # free up memory
    del json_data

    comprehend_chunks, paragraphs = chunk_up_transcript(custom_vocabs, results)

    start = time.time()
    detected_entities_response = comprehend.batch_detect_entities(TextList=comprehend_chunks, LanguageCode='en')
    round_trip = time.time() - start
    logging.info('End of batch_detect_entities. Took time {:10.4f}\n'.format(round_trip))

    entities = parse_detected_entities_response(detected_entities_response, {})
    entities_as_list = {}
    for entity_type in entities:
        entities_as_list[entity_type] = list(entities[entity_type])

    clean_up_entity_results(entities_as_list)
    print(json.dumps(entities_as_list, indent=4))

    # start = time.time()
    # detected_phrase_response = comprehend.batch_detect_key_phrases(TextList=comprehend_chunks, LanguageCode='en')
    # round_trip = time.time() - start
    # logging.info('End of batch_detect_key_phrases. Took time {:10.4f}\n'.format(round_trip))

    # key_phrases = parse_detected_key_phrases_response(detected_phrase_response)
    # logging.debug(json.dumps(key_phrases, indent=4))

    doc_to_update = {'transcript': paragraphs}
    doc_to_update['transcript_entities'] = entities_as_list
    logging.info(doc_to_update)
    # doc_to_update['key_phrases'] = key_phrases
    key = 'podcasts/transcript/' + id_generator() + '.json'

    response = s3_client.put_object(Body=json.dumps(doc_to_update, indent=2), Bucket=bucket, Key=key)
    logging.info(response)

    logging.info("successfully written transcript to s3://" + bucket + "/" + key)
    # Return the bucket and key of the transcription / comprehend result.
    transcript_location = {"bucket": bucket, "key": key}
    return transcript_location



def chunk_up_transcript(custom_vocabs, results):
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
    #     "speaker_labels": {
    #       "speakers": 2,
    #       "segments": [
    #         {
    #           "start_time": "0.0",
    #           "speaker_label": "spk_1",
    #           "end_time": "23.84",
    #           "items": [
    #               {
    #                   "start_time": "23.84",
    #                   "speaker_label": "spk_0",
    #                   "end_time": "24.87",
    #                   "items": [
    #                       {
    #                           "start_time": "24.063",
    #                           "speaker_label": "spk_0",
    #                           "end_time": "24.273"
    #                       },
    #                       {
    #                           "start_time": "24.763",
    #                           "speaker_label": "spk_0",
    #                           "end_time": "25.023"
    #                       }
    #                   ]
    #               }
    #           ]
    #         ]
    #      },
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


    speaker_label_exist = False
    speaker_segments = None
    if 'speaker_labels' in results:
        speaker_label_exist = True
        speaker_segments = parse_speaker_segments(results)

    items = results['items']
    last_speaker = None
    paragraphs = []
    current_paragraph = ""
    comprehend_chunks = []
    current_comprehend_chunk = ""
    previous_time = 0
    last_pause = 0
    last_item_was_sentence_end = False
    for item in items:
        if item["type"] == "pronunciation":
            start_time = float(item['start_time'])

            if speaker_label_exist:
                current_speaker = get_speaker_label(speaker_segments, float(item['start_time']))
                if last_speaker is None or current_speaker != last_speaker:
                    if current_paragraph is not None:
                        paragraphs.append(current_paragraph)
                    current_paragraph = current_speaker + " :"
                    last_pause = start_time
                last_speaker = current_speaker

            elif (start_time - previous_time) > 2 or (
                            (start_time - last_pause) > 15 and last_item_was_sentence_end):
                last_pause = start_time
                if current_paragraph is not None or current_paragraph != "":
                    paragraphs.append(current_paragraph)
                current_paragraph = ""

            phrase = item['alternatives'][0]['content']
            if custom_vocabs is not None:
                if phrase in custom_vocabs:
                    phrase = custom_vocabs[phrase]
                    logging.info("replaced custom vocab: " + phrase)
            if phrase in commonDict:
                phrase = commonDict[phrase]
            current_paragraph += " " + phrase

            # add chunking
            current_comprehend_chunk += " " + phrase

            last_item_was_sentence_end = False

        elif item["type"] == "punctuation":
            current_paragraph += item['alternatives'][0]['content']
            current_comprehend_chunk += item['alternatives'][0]['content']
            if item['alternatives'][0]['content'] in (".", "!", "?"):
                last_item_was_sentence_end = True
            else:
                last_item_was_sentence_end = False

        if (item["type"] == "punctuation" and len(current_comprehend_chunk) >= 4500) \
                or len(current_comprehend_chunk) > 4900:
            comprehend_chunks.append(current_comprehend_chunk)
            current_comprehend_chunk = ""

        if 'end_time' in item:
            previous_time = float(item['end_time'])

    if not current_comprehend_chunk == "":
        comprehend_chunks.append(current_comprehend_chunk)
    if not current_paragraph == "":
        paragraphs.append(current_paragraph)

    logging.debug(paragraphs)
    logging.debug(comprehend_chunks)

    return comprehend_chunks, "\n\n".join(paragraphs)


def parse_detected_key_phrases_response(detected_phrase_response):
    if 'ErrorList' in detected_phrase_response and len(detected_phrase_response['ErrorList']) > 0:
        logging.error("encountered error during batch_detect_key_phrases")
        logging.error(detected_phrase_response['ErrorList'])

    if 'ResultList' in detected_phrase_response:
        result_list = detected_phrase_response["ResultList"]
        phrases_set = set()
        for result in result_list:
            phrases = result['KeyPhrases']
            for detected_phrase in phrases:
                if float(detected_phrase["Score"]) >= ENTITY_CONFIDENCE_THRESHOLD:
                    phrase = detected_phrase["Text"]
                    phrases_set.add(phrase)
        key_phrases = list(phrases_set)
        return key_phrases
    else:
        return []


def clean_up_entity_results(entities_as_list):
    if 'PERSON' in entities_as_list:
        try:
            people = entities_as_list['PERSON']
            duplicates = find_duplicate_person(people)
            for d in duplicates:
                people.remove(d)
            entities_as_list['PERSON'] = people
        except Exception as e:
            logging.error(e)
    if 'COMMERCIAL_ITEM' in entities_as_list:
        entities_as_list['Products_and_Titles'] = entities_as_list['COMMERCIAL_ITEM']
        del entities_as_list['COMMERCIAL_ITEM']
    if 'TITLE' in entities_as_list:
        if 'PRODUCTS / TTTLES' in entities_as_list:
            entities_as_list['Products_and_Titles'].append(entities_as_list['TITLE'])
        else:
            entities_as_list['Products_and_Titles'] = entities_as_list['TITLE']
        del entities_as_list['TITLE']


def parse_detected_entities_response(detected_entities_response, entities):
    if 'ErrorList' in detected_entities_response and len(detected_entities_response['ErrorList']) > 0:
        logging.error("encountered error during batch_detect_entities")
        logging.error(detected_entities_response['ErrorList'])

    if 'ResultList' in detected_entities_response:
        result_list = detected_entities_response["ResultList"]
        # entities = {}
        for result in result_list:
            detected_entities = result["Entities"]
            for detected_entity in detected_entities:
                if float(detected_entity["Score"]) >= ENTITY_CONFIDENCE_THRESHOLD:

                    entity_type = detected_entity["Type"]

                    if entity_type != 'QUANTITY':
                        text = detected_entity["Text"]

                        if entity_type == 'LOCATION' or entity_type == 'PERSON' or entity_type == 'ORGANIZATION':
                            if not text.isupper():
                                text = string.capwords(text)

                        if entity_type in entities:
                            entities[entity_type].add(text)
                        else:
                            entities[entity_type] = set([text])
        return entities
    else:
        return {}


def get_speaker_label(speaker_segments, start_time):
    for segment in speaker_segments:
        if segment['start_time'] <= start_time < segment['end_time']:
            return segment['speaker']
    return None


def parse_speaker_segments(results):
    speaker_labels = results['speaker_labels']['segments']
    speaker_segments = []
    for label in speaker_labels:
        segment = dict()
        segment["start_time"] = float(label["start_time"])
        segment["end_time"] = float(label["end_time"])
        segment["speaker"] = label["speaker_label"]
        speaker_segments.append(segment)
    return speaker_segments


def lambda_handler(event, context):
    """
        AWS Lambda handler

    """
    log_level = str(os.environ.get('LOG_LEVEL')).upper()
    if log_level not in [
                        'DEBUG', 'INFO',
                        'WARNING', 'ERROR',
                        'CRITICAL'
                    ]:
      log_level = 'INFO'
    logging.getLogger().setLevel(log_level)

    logging.debug(event)

    # Pull the signed URL for the payload of the transcription job
    transcription_url = event['transcriptionUrl']

    vocab_info = None
    if 'vocabularyInfo' in event:
        vocab_info = event['vocabularyInfo']
    transcript_location = process_transcript(transcription_url,  vocab_info)

    retVal = {
        "mediaS3Location": {
            "bucket": event['mediaS3Location']['bucket'],
            "key": event['mediaS3Location']['key']
        },
        "content_type": event['content_type'],
        "transcribeJob": event['transcribeJob'],
        "transcriptionUrl": event['transcriptionUrl'],
        "bucket": transcript_location["bucket"],
        "key": transcript_location["key"]
    }
    logging.debug(retVal)
    return retVal
