import boto3
import random
import string
import json
import cfnresponse
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

cognito_idp_client = boto3.client('cognito-idp')


# Generates a random ID
def id_generator(size=12, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def pwd_generator(size=8):
    lowerChars = string.ascii_lowercase
    upperChars = string.ascii_uppercase
    digits = string.digits
    specials = '%$#&[]'
    return random.choice(lowerChars) + random.choice(upperChars) + random.choice(digits) + random.choice(
        specials) + random.choice(lowerChars) + random.choice(upperChars) + random.choice(digits) + random.choice(
        specials)


def configure_cognito_lambda_handler(event, context):
    logger.info("Received event: %s" % json.dumps(event))

    try:
        if event['RequestType'] == 'Create':
            create_response = create(event)
            cfnresponse.send(event, context, cfnresponse.SUCCESS, create_response)
        if event['RequestType'] == 'Update':
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {"DashboardUser": '',"DashboardPassword": ''})
        elif event['RequestType'] == 'Delete':
            result_status = delete(event)
            cfnresponse.send(event, context, result_status, {})
    except:
        logger.error("Error", exc_info=True)
        cfnresponse.send(event, context, cfnresponse.FAILED, {})


def create(event):
    user_pool_id = event['ResourceProperties']['UserPoolId']

    dashboard_user, dashboard_password, dashboard_email = get_user_credentials(event)
    add_user(user_pool_id, dashboard_user, dashboard_email, dashboard_password)
    return {
        "DashboardUser": dashboard_user,
        "DashboardPassword": dashboard_password}


def delete(event):
    return cfnresponse.SUCCESS


def get_user_credentials(event):
    if 'DashboardUser' in event['ResourceProperties'] and event['ResourceProperties']['DashboardUser'] != '':
        DashboardUser = event['ResourceProperties']['DashboardUser']
    else:
        DashboardUser = 'admin'

    if 'DashboardEmail' in event['ResourceProperties'] and event['ResourceProperties']['kibDashboardEmailanaEmail'] != '':
        DashboardEmail = event['ResourceProperties']['DashboardEmail']
    else:
        DashboardEmail = id_generator(6) + '@example.com'

    DashboardPassword = pwd_generator()
    return DashboardUser, DashboardPassword, DashboardEmail


def add_user(userPoolId, DashboardUser, DashboardEmail, DashboardPassword):
    cognito_response = cognito_idp_client.admin_create_user(
        UserPoolId=userPoolId,
        Username=DashboardUser,
        UserAttributes=[
            {
                'Name': 'email',
                'Value': DashboardEmail
            },
            {
                'Name': 'email_verified',
                'Value': 'True'
            }
        ],
        TemporaryPassword=DashboardPassword,
        MessageAction='SUPPRESS',
        DesiredDeliveryMediums=[
            'EMAIL'
        ]
    )
    logger.info("create Cognito user {} for user pool {} successful.".format(DashboardUser, userPoolId))
    return cognito_response
