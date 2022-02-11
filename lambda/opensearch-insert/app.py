from __future__ import print_function

import boto3
import json
import os
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy import helpers
from requests_aws4auth import AWS4Auth
import logging
import time

# Parameters
REGION = os.getenv('AWS_REGION', default='us-east-1')

# Pull environment data for the OS domain
osendpoint = os.environ['OS_DOMAIN']
bucket = os.environ['BUCKET_NAME']

# get the Elasticsearch index name from the environment variables
FULL_EPISODE_INDEX = os.getenv('ES_EPISODE_INDEX', default='episodes')
# get the Elasticsearch index name from the environment variables
PARAGRAPHS_INDEX = os.getenv('ES_PARAGRAPH_INDEX', default='paragraphs')

s3_client = boto3.client('s3')



service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, REGION, service, session_token=credentials.token)

client = OpenSearch(
    hosts = [{'host': osendpoint, 'port': 443}],
    http_auth = awsauth,
    use_ssl = True,
    verify_certs = True,
    connection_class = RequestsHttpConnection
)

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

    # Pull the keywords S3 location for the payload of the previous lambda function
    index_keywords(event[0])
    index_episode(event[1])
    # Episode level payload

    return event


def index_episode(event):
    response = s3_client.get_object(Bucket=bucket, Key=event["key"])
    file_content = response['Body'].read().decode('utf-8')
    fullepisode = json.loads(file_content)

    doc = {
        "YouTubeVideoID": event["metadata"]["YouTubeVideoID"],
        "Title": event["metadata"]["Title"],
        "Name": event["metadata"]["Name"],
        "PublishDate": event["metadata"]["PublishDate"],
        "YouTubeURL": event["metadata"]["YouTubeURL"],
        "ProcessedVideoKey": event["metadata"]["Name"] + ".mp4",
        'transcript': fullepisode['transcript'],
        # 'transcript_entities': fullepisode['transcript_entities'],
        # 'key_phrases': fullepisode['key_phrases']
    }

    logging.info("request")
    logging.debug(json.dumps(doc))
    # add the document to the index
    start = time.time()
    res = client.index(index=FULL_EPISODE_INDEX,
                   body=doc, id=event["metadata"]["YouTubeVideoID"])
    logging.info("response")
    logging.info(json.dumps(res, indent=4))
    logging.info('REQUEST_TIME es_client.index {:10.4f}'.format(time.time() - start))


def index_keywords(event):

    response = s3_client.get_object(Bucket=bucket, Key=event['key'])
    file_content = response['Body'].read().decode('utf-8')
    keywords = json.loads(file_content)
    actions = []
    # Iterate through all the keywords and create an index document for each phrase
    for i in range(len(keywords)):
        keyword = keywords[i]["text"]
        tags = keywords[i]["tags"]
        key_phrases = keywords[i]["key_phrases"]
        # Offset the time that the word was spoken to the listener has some context to the phrase
        time = str(max(float(keywords[i]["startTime"]), 0))
        actions.append({
            "_index": PARAGRAPHS_INDEX,
            "_type": "_doc",
            "_id": event["metadata"]["YouTubeVideoID"] + "_" + time,
            "_source": {
                "YouTubeVideoID": event["metadata"]["YouTubeVideoID"],
                "Title": event["metadata"]["Title"],
                "Name": event["metadata"]["Name"],
                "PublishDate": event["metadata"]["PublishDate"],
                "YouTubeURL": event["metadata"]["YouTubeURL"],
                "ProcessedVideoKey": event["metadata"]["Name"] + ".mp4",
                "text": keyword,
                "tags": tags,
                "key_phrases": key_phrases,
                "speaker": keywords[i]["speaker"],
                "startTime": float(time)
            }
        })

    # Bulk load the documents into the index.
    result = helpers.bulk(client, actions)

    logging.info("indexed keywords to ES")
    logging.info(json.dumps(result, indent=2))
    return result


