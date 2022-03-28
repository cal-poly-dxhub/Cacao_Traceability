import boto3
import json
import logging
import os
import time

# Configure logging. 
# LOG_LEVEL environment variable can be used to override the default level of INFO
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

REGION = os.environ.get('AWS_REGION')
pinpoint = boto3.client('pinpoint', REGION)
lex = boto3.client('lexv2-runtime', REGION)

PINPOINT_APPLICATION = os.environ.get('PINPOINT_APPLICATION')
LEX_BOT_ID = os.environ.get('LEX_BOT_ID')
LEX_BOT_ALIAS = os.environ.get('LEX_BOT_ALIAS')

# LEX_BOT_ALIAS="TSTALIASID"
# LEX_BOT_ID="HHIVXSASZT"
# PINPOINT_APPLICATION="686caf3d3c514bd5bb1a25d60f17b478"

logger.debug("ENV PINPOINT_APPLICATION=%s LEX_BOT_ID=%s LEX_BOT_ALIAS=%s",PINPOINT_APPLICATION, LEX_BOT_ID, LEX_BOT_ALIAS)

def sendResponse(response_str, customerPhoneNumber,chatbotPhoneNumber):
    logger.debug("Sending response=%s",response_str)
    pinpoint_args = {
            'ApplicationId': PINPOINT_APPLICATION,
            'MessageRequest': {
                'Addresses': {
                    customerPhoneNumber : {
                        'ChannelType': 'SMS'
                    }
                },
                'MessageConfiguration': {
                    'SMSMessage': { 
                        'MessageType': 'TRANSACTIONAL',
                        'Body': response_str,
                        'OriginationNumber': chatbotPhoneNumber
                    }
                }
            }
        }

    logger.debug("Sending message with=%s",pinpoint_args)
    result = pinpoint.send_messages(**pinpoint_args)

def sendSNSFromPinpointToLex(sns_event):
    # Building out a dictionary (response) as return value as follows:
    #{ "customerPhoneNumber": "<originating phone number (country code 10 digit #",
    #   "chatbotPhoneNumber": "<number that was texted (country code 10 digit #",
    #   "lex_response" : "Message sent back from lex"}

    response = {}
    received_message = sns_event['Records'][0]['Sns']
    message = sns_event['Records'][0]['Sns']['Message']
    # Locally this was a dict but a str in AWS?
    if isinstance(message, str):
        message = json.loads(sns_event['Records'][0]['Sns']['Message'])
    #print("DEK",type(message))
    #print("DEK",message)
    response['customerPhoneNumber'] = message['originationNumber']
    response['chatbotPhoneNumber'] = message['destinationNumber']
    user_message = message['messageBody'].lower()
    phone_as_session = response['customerPhoneNumber'].replace("+1", "")
       
    logger.debug("Received SNS message: %s", received_message)
    logger.debug("UserID: %s", phone_as_session)
    logger.debug("user_message: %s", user_message)
    logger.debug("Phone: %s", response['customerPhoneNumber'])
    
    # Send Lex V2 our text message 
    response["lex_response"] = lex.recognize_text(
        botId=LEX_BOT_ID,
        botAliasId=LEX_BOT_ALIAS,
        localeId='en_US',
        sessionId=phone_as_session,
        text=user_message
    )
    logger.debug("Returning lex_response=%s", response["lex_response"] )

    return response

def lambda_handler(event, context):
    
    logger.debug('Event={}'.format(event))

    lex_data = sendSNSFromPinpointToLex(event)

    if(lex_data["lex_response"]["ResponseMetadata"]["HTTPStatusCode"]==200):
        lex_reponse_msg = lex_data["lex_response"]["messages"][0]["content"]
        sendResponse(lex_reponse_msg,lex_data["customerPhoneNumber"],lex_data["chatbotPhoneNumber"])
    else:
        sendResponse("Sorry an error occurred please try again later",lex_data["customerPhoneNumber"],lex_data["chatbotPhoneNumber"])

