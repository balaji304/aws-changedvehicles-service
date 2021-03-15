import os
import sys
import logging
from boto3.dynamodb.conditions import Key, Attr
logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


CWD = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, CWD)

from main import *



class HeplerImporter(Helper):
    def get_vehicleids(self, eventData, sourceObj):
        result = eventData[KEY_NAME]
        return result


    def get_eventType(self, eventData, sourceObj):
        recordtypeId = eventData.get('RecordTypeId', None)
        return recordtypeId


def handler(event, context):
    logger.info("Processing Started....")
    messages = event["Records"]
    helper = HeplerImporter()
    helper.process_sqs_to_sns(messages)


if __name__ == "__main__":
    SourceSqsUrl = 'https://sqs.eu-central-1.amazonaws.com/831745121203/Refi2-TopicSubscriber-staging-changedvehicles-service-Queue'
    client = boto3.client('sqs', region_name=AWS_REGION)
    response = client.receive_message(
        QueueUrl=SourceSqsUrl,
        VisibilityTimeout=30,
        WaitTimeSeconds=5,
        MaxNumberOfMessages=10
    )
    messages = response['Messages']
    for message in messages:
        for key, n_key in zip(['ReceiptHandle', 'MessageId', 'Body'], ['receiptHandle', 'messageId', 'body']):
            message[n_key] = message.pop(key)
    if messages:
        event = {'Records': messages}
        handler(event, "h")
