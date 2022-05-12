import os
import logging
import pyqldb

from pyqldb.driver.qldb_driver import QldbDriver
from db_utility import recordNextVisit, getMarketPriceDB, getLastPickupDetails

qldb_driver = QldbDriver(ledger_name='cacao-ledger-test')

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def get_slots(intent_request):
    return intent_request['sessionState']['intent']['slots']
    
def get_slot(intent_request, slotName):
    slots = get_slots(intent_request)
    if slots is not None and slotName in slots and slots[slotName] is not None:
        return slots[slotName]['value']['interpretedValue']
    else:
        return None    

def get_session_attributes(intent_request):
    sessionState = intent_request['sessionState']
    if 'sessionAttributes' in sessionState:
        return sessionState['sessionAttributes']

    return {}

def elicit_intent(intent_request, session_attributes, message):
    return {
        'sessionState': {
            'dialogAction': {
                'type': 'ElicitIntent'
            },
            'sessionAttributes': session_attributes
        },
        'messages': [ message ] if message != None else None,
        'requestAttributes': intent_request['requestAttributes'] if 'requestAttributes' in intent_request else None
    }

def close(intent_request, session_attributes, fulfillment_state, message):
    intent_request['sessionState']['intent']['state'] = fulfillment_state
    return {
        'sessionState': {
            'sessionAttributes': session_attributes,
            'dialogAction': {
                'type': 'Close'
            },
            'intent': intent_request['sessionState']['intent']
        },
        'messages': [message],
        'sessionId': intent_request['sessionId'],
        'requestAttributes': intent_request['requestAttributes'] if 'requestAttributes' in intent_request else None
    }
def findFarmersBuckets(transaction_executor, farmerID):
    cursor = transaction_executor.execute_statement("SELECT * FROM transactions WHERE farmerId = ?", farmerID)
    count = 0
    for bucket in cursor:
        print (bucket)
        count = count + 1        
    return count

def ReviewLastPickupDetails(intent_request):
    session_attributes = get_session_attributes(intent_request)
    slots = get_slots(intent_request)
    logger.debug('Slots={}'.format(slots))
    calling_number = ""
    number_of_trans = slots["Trans"]["value"]["interpretedValue"]
    logger.debug('Trans={}'.format(number_of_trans))
    #count = qldb_driver.execute_lambda(lambda executor: findFarmersBuckets(executor, "d2066964-a2b3-4ab8-9783-f4f40bdc3b3e"))
    # text = ""
    # if count == 0:
    #     text = "There where no recorded pickups today."
    # elif count == 1:
    #      text = "We recorded " + str(count) + " bucket picked up today.  Thanks for your business."
    # else:
    #     text = "We recorded " + str(count) + " buckets picked up today.  Thanks for your business."
    try:
        # Grab caller number from the corresponding object
        if "Connect" == intent_request["requestAttributes"]["x-amz-lex:channels:platform"]:
                calling_number = intent_request["sessionState"]["sessionAttributes"]["InboundCallerID"]
                calling_number = calling_number.replace("+", "")
    # Calling number stored as sessionId from pinpoint
    except KeyError as e:
        calling_number = intent_request["sessionId"]
    text = getLastPickupDetails(calling_number, number_of_trans)
    message =  {
            'contentType': 'PlainText',
            'content': text
        }

    fulfillment_state = "Fulfilled"    
    return close(intent_request, session_attributes, fulfillment_state, message)


def SchedulePickup(intent_request):
    session_attributes = get_session_attributes(intent_request)
    slots = get_slots(intent_request)
    logger.debug('Slots={}'.format(slots))
    
    calling_number = ""
    text = "You got it!"
    visit_type = ""
    visit_timestamp = ""
    fulfillment_state = "Fulfilled"  

    try:
        # Grab caller number from the corresponding object
        if "Connect" == intent_request["requestAttributes"]["x-amz-lex:channels:platform"]:
                calling_number = intent_request["sessionState"]["sessionAttributes"]["InboundCallerID"]
                calling_number = calling_number.replace("+", "")
    # Calling number stored as sessionId from pinpoint
    except KeyError as e:
        calling_number = intent_request["sessionId"]
    try:
        visit_type = slots["AppointmentType"]["value"]["interpretedValue"]
        visit_timestamp = slots["Date"]["value"]["interpretedValue"] + " " + slots["Time"]["value"]["interpretedValue"]
        recordNextVisit(calling_number, visit_type, visit_timestamp)
    except:
          text = "I was unable to schedule your appointment please try again later!"
          fulfillment_state = "Failed" 
    
    message =  {
            'contentType': 'PlainText',
            'content': text
        }

       
    return close(intent_request, session_attributes, fulfillment_state, message)

def getPrice(intent_request):
    session_attributes = get_session_attributes(intent_request)
    fulfillment_state = "Failed" 
    text = "Current market price is " + getMarketPriceDB() + " Colombian pesos"
    fulfillment_state = "Fulfilled"  
    message =  {
            'contentType': 'PlainText',
            'content': text
        }

       
    return close(intent_request, session_attributes, fulfillment_state, message)    
def dispatch(intent_request):
    intent_name = intent_request['sessionState']['intent']['name']
    response = None

    if intent_name == 'ReviewLastPickupDetails':
        return ReviewLastPickupDetails(intent_request)
    elif intent_name == 'ScheduleVisit':
        return SchedulePickup(intent_request)
    elif intent_name == 'Price':
        return getPrice(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')

def lambda_handler(event, context):
    logger.debug('Event={}'.format(event))
    response = dispatch(event)
    return response

