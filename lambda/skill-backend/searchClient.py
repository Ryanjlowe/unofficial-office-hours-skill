from curses import meta
import boto3
import json
import os
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import logging


# Parameters
REGION = os.getenv('AWS_REGION', default='us-east-1')

# Pull environment data for the OS domain
osendpoint = os.environ['OS_DOMAIN']

# get the Elasticsearch index name from the environment variables
FULL_EPISODE_INDEX = os.getenv('ES_EPISODE_INDEX', default='episodes')
# get the Elasticsearch index name from the environment variables
PARAGRAPHS_INDEX = os.getenv('ES_PARAGRAPH_INDEX', default='paragraphs')


TABLE_NAME = os.environ['TABLE_NAME']
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

CDN_URL = os.environ['CDN_URL']


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

def perform_search(search_term):

    query = {
        "size": 0,
        "_source": ["YouTubeVideoID", "Title", "Name", "PublishDate", "YouTubeURL", "ProcessedVideoKey", "text", "startTime"],
        "query": {
            "function_score": {
            "query":{
                "bool": {
                "should": [
                    {
                                
                    "query_string": {
                        "query": search_term
                        ,"boost": 10
                    }
                    }
                ]
                }
            },
            "functions": [
                {
                "weight": 5,
                "linear": {
                    "PublishDate": {
                    "scale": "2000d",
                    "decay": 0.8
                    }
                }
                }
            ]
            }
        },
        "aggs": {
            "episode": {
            "terms": {
                "field": "YouTubeVideoID",
                "order": {
                "top_hit": "desc"
                }
                
            },
            "aggs": {
                "top_episode_hits": {
                "top_hits": {
                    "_source": {
                    "include": ["YouTubeVideoID", "Title", "Name", "PublishDate", "YouTubeURL", "ProcessedVideoKey", "text", "startTime"]
                    }
                }
                },
                "top_hit": {
                "max": {
                    "script": {
                    "source": "_score"
                    }
                }
                }
            }
            }
        }
    }

    logging.info(json.dumps(query))

    response = client.search(
        body = query,
        index = PARAGRAPHS_INDEX
    )
    logging.info('\nSearch results:')
    logging.info(json.dumps(response))


    retVal = []

    buckets = response["aggregations"]["episode"]["buckets"]

    for bucket in buckets:
        youtubeVideoId = bucket['key']
        metadata = get_metadata(youtubeVideoId)

        episode = {
            'title': metadata['title'],
            'description': metadata['description'],
            'lengthInSeconds': 3600000 if 'lengthInSeconds' not in metadata else metadata['lengthInSeconds'],
            'url': CDN_URL +  metadata['name'] + '.mp4',
            'publish_date': metadata['publishDate'],
            'results': []
        }

        hits = bucket["top_episode_hits"]["hits"]["hits"]

        for hit in hits:
            source = hit['_source']   
            episode['results'].append({
                # 'url': CDN_URL + source['ProcessedVideoKey'],
                'offset': source["startTime"] * 1000
            })


        retVal.append(episode)


    logging.info(retVal)


    return retVal



def get_metadata(youtubeVideoId):

    response = table.get_item(
        Key={
            'id': youtubeVideoId
        }
    )
    return response['Item']


