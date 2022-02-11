from __future__ import print_function

import boto3
import json
import os
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import logging
import time
import cfnresponse

# Parameters
REGION = os.getenv('AWS_REGION', default='us-east-1')

# Pull environment data for the OS domain
osendpoint = os.environ['OS_DOMAIN']

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




def create_episode_index():
    mappings = '''
    {
        "mappings": {
            "properties" : {
                "Name" : {
                    "type" : "text"
                },
                "ProcessedVideoKey" : {
                    "type" : "keyword"
                },
                "PublishDate" : {
                    "type" : "date"
                },
                "Title" : {
                    "type" : "text"
                },
                "YouTubeURL" : {
                    "type" : "keyword"
                },
                "YouTubeVideoID" : {
                    "type" : "keyword"
                },
                "key_phrases" : {
                    "type": "nested",
                    "properties" : {
                        "BeginOffset" : {
                            "type" : "long"
                        },
                        "EndOffset" : {
                            "type" : "long"
                        },
                        "Score" : {
                            "type" : "float"
                        },
                        "Text" : {
                            "type" : "text",
                            "fields" : {
                                "keyword" : {
                                "type" : "keyword",
                                "ignore_above" : 256
                                }
                            }
                        }
                    }
                },
                "transcript" : {
                    "type" : "text"
                },
                "transcript_entities" : {
                    "properties" : {
                        "DATE" : {
                            "type" : "text",
                            "fields" : {
                                "keyword" : {
                                "type" : "keyword",
                                "ignore_above" : 256
                                }
                            }
                        },
                        "LOCATION" : {
                            "type" : "text",
                            "fields" : {
                                "keyword" : {
                                "type" : "keyword",
                                "ignore_above" : 256
                                }
                            }
                        },
                        "ORGANIZATION" : {
                            "type" : "text",
                            "fields" : {
                                "keyword" : {
                                "type" : "keyword",
                                "ignore_above" : 256
                                }
                            }
                        },
                        "OTHER" : {
                            "type" : "text",
                            "fields" : {
                                "keyword" : {
                                "type" : "keyword",
                                "ignore_above" : 256
                                }
                            }
                        },
                        "PERSON" : {
                            "type" : "text",
                            "fields" : {
                                "keyword" : {
                                "type" : "keyword",
                                "ignore_above" : 256
                                }
                            }
                        },
                        "Products_and_Titles" : {
                            "type" : "text",
                            "fields" : {
                                "keyword" : {
                                "type" : "keyword",
                                "ignore_above" : 256
                                }
                            }
                        }
                    }
                }
            }
        }
    }'''
    
    start = time.time()
    logging.info("mappings to create for index: " + mappings)
    res = client.indices.create(index=FULL_EPISODE_INDEX, body=mappings)
    round_trip = time.time() - start
    logging.info(json.dumps(res, indent=2))
    logging.info('REQUEST_TIME es_client.indices.create {:10.4f}'.format(round_trip))

def create_paragraph_index():
    mappings = '''
    {
        "mappings": {
            "properties" : {
                "Name" : {
                    "type" : "text"
                },
                "ProcessedVideoKey" : {
                    "type" : "keyword"
                },
                "PublishDate" : {
                    "type" : "date"
                },
                "Title" : {
                    "type" : "text"
                },
                "YouTubeURL" : {
                    "type" : "keyword"
                },
                "YouTubeVideoID" : {
                    "type" : "keyword"
                },
                "key_phrases" : {
                    "type": "nested",
                    "properties" : {
                        "BeginOffset" : {
                            "type" : "long"
                        },
                        "EndOffset" : {
                            "type" : "long"
                        },
                        "Score" : {
                            "type" : "float"
                        },
                        "Text" : {
                            "type" : "text",
                            "fields" : {
                                "keyword" : {
                                "type" : "keyword",
                                "ignore_above" : 256
                                }
                            }
                        }
                    }
                },
                "media_url" : {
                    "type" : "keyword"
                },
                "published_time" : {
                    "type" : "date",
                    "format" : "yyyy:MM:dd HH:mm:ss"
                },
                "speaker" : {
                    "type" : "keyword"
                },
                "startTime" : {
                    "type" : "float"
                },
                "tags" : {
                    "type" : "text",
                    "fields" : {
                        "keyword" : {
                        "type" : "keyword",
                        "ignore_above" : 256
                        }
                    }
                },
                "text" : {
                    "type" : "text"
                }
            }
        }
    }'''


    start = time.time()
    logging.info("mappings to create for index: " + mappings)
    res = client.indices.create(index=PARAGRAPHS_INDEX, body=mappings)
    round_trip = time.time() - start
    logging.info(json.dumps(res, indent=2))
    logging.info('REQUEST_TIME es_client.indices.create {:10.4f}'.format(round_trip))


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

    try:
        if event['RequestType'] == 'Create':
            if not client.indices.exists(index=FULL_EPISODE_INDEX):
                create_episode_index()
            else:
                logging.info("index " + FULL_EPISODE_INDEX + " already exists. skipping index creation.")

            if not client.indices.exists(index=PARAGRAPHS_INDEX):
                create_paragraph_index()
            else:
                logging.info("index " + FULL_EPISODE_INDEX + " already exists. skipping index creation.")

            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})

        if event['RequestType'] == 'Update':
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        elif event['RequestType'] == 'Delete':
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
    except:
        logging.error("Error", exc_info=True)
        cfnresponse.send(event, context, cfnresponse.FAILED, {})
