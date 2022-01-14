import cfnresponse
import os
import logging
import traceback
import boto3
import json
import time

transcribe_client = boto3.client('transcribe')

def lambda_handler(event, context):

    log_level = str(os.environ.get('LOG_LEVEL')).upper()
    if log_level not in [
                      'DEBUG', 'INFO',
                      'WARNING', 'ERROR',
                      'CRITICAL'
                  ]:
      log_level = 'DEBUG'
    logging.getLogger().setLevel(log_level)

    logging.debug(event)

    try:
        if event['ResourceProperties']['CustomResourceAction'] == 'CreateVocab':

            vocabularyName = os.environ.get('TRANSCRIBE_VOCAB_NAME')
            vocabularyTerms = os.environ.get('TRANSCRIBE_VOCAB_TERMS').split(",")

            if event['RequestType'] == 'Create':
                # Create the vocab

                response = transcribe_client.create_vocabulary(
                    VocabularyName=vocabularyName,
                    LanguageCode='en-US',
                    Phrases=vocabularyTerms
                )
                logging.info(response)

            elif event['RequestType'] == 'Delete':
                # Delete the vocab

                response = client.delete_vocabulary(
                    VocabularyName=vocabularyName
                )
                logging.info(response)

            cfnresponse.send(event, context, cfnresponse.SUCCESS, {"success": True}, 'CreateVocab')
        else:
            logging.error('Missing CustomResourceAction - no action to perform')
            cfnresponse.send(event, context, cfnresponse.FAILED, {"success": False, "error": "Missing CustomResourceAction"}, "error")

    except Exception as error:
        logging.error('lambda_handler error: %s' % (error))
        logging.error('lambda_handler trace: %s' % traceback.format_exc())
        cfnresponse.send(event, context, cfnresponse.FAILED, {"success": False, "error": "See Lambda Logs"}, "error")
