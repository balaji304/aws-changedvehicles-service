import os
import boto3
import json
from datetime import datetime
from abc import ABCMeta, abstractmethod
import logging
logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)


AWS_REGION = os.environ.get('AWS_REGION', 'eu-central-1')
STAGE = os.environ.get('STAGE')
TOPIC_ARN = os.getenv("TOPIC_ARN")
SOURCESQSURL = os.getenv('SOURCESQSURL')
KEY_NAME = os.getenv("KEY_NAME")
SOURCE_OBJ = os.getenv("SF_OBJNAME")

class Helper:
    def __init__(self):
        self.sqsClient = boto3.client('sqs', region_name=AWS_REGION)
        self.dynamoClient = boto3.client('dynamodb', region_name=AWS_REGION)
        self.dynamoResourceClient = boto3.resource('dynamodb', region_name=AWS_REGION)


    def extract_event_data_mgsid(self, message):
        MessageId = message['messageId']
        Message = json.loads(message['body']).get('Message')
        payload = json.loads(Message).get('payload')
        event_data = payload['EventData']
        eventSourceARN = message.get('eventSourceARN')
        return event_data, MessageId, eventSourceARN


    @abstractmethod
    def get_vehicleids(self, *kwargs):
        raise ImportWarning


    @abstractmethod
    def get_eventType(self, *kwargs):
        raise ImportWarning


    def transform_to_sns_msg(self, event_data, eventSourceARN):
        dic = {}
        dic['metadata'] = {
            "SourceObject": SOURCE_OBJ,
            "SourceObjectId": event_data.get("Id"),
            "SourceObjectRecordType": self.get_eventType(event_data, SOURCE_OBJ),
            "timestamp":  datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z'),
            "sourceQueueArn": eventSourceARN
        }
        dic['eventdata'] = {
            "vehicleIds" : self.get_vehicleids(event_data, SOURCE_OBJ)
        }
        return dic


    def publish_mgs_to_sns_topic(self, msg, topicArn):
        client = boto3.client('sns', region_name=AWS_REGION)
        response = client.publish(
                TargetArn=topicArn,
                Message=json.dumps({'default': json.dumps(msg)}),
                MessageStructure='json'
            )
        return response


    def process_msg_to_sns_topic(self, msg, TOPIC_ARN):
        response = self.publish_mgs_to_sns_topic(msg, TOPIC_ARN)
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return True


    def map_target_successes_to_source_sqs_delete_list(self, messages, success_ids):
        delete_mapping_list = []
        for i in range(0, len(messages)):
            message_id = messages[i]['messageId']
            receiptHandle = messages[i]['receiptHandle']
            if message_id in success_ids:
                delete_mapping_list.append(
                    {'Id': message_id, 'ReceiptHandle': receiptHandle})
        return delete_mapping_list


    def delete_sqs_batch_message(self, sqs_delete_list, queueUrl):
        sqs_client = self.sqsClient
        response = sqs_client.delete_message_batch(
            QueueUrl=queueUrl,
            Entries=sqs_delete_list
        )

    def scan_dynamo_table_with_filter(self, tableName):
        pass

    def process_message(self, message):
        logger.info(f"Extracting Payload from SQS Message..")
        event_data, sns_msgid, eventSourceARN = self.extract_event_data_mgsid(message)
        logger.info(f"SQS MessageId: {sns_msgid}")
        topic_msg = self.transform_to_sns_msg(event_data, SOURCE_OBJ, eventSourceARN)
        response = self.process_msg_to_sns_topic(topic_msg, TOPIC_ARN)
        if response:
            logger.info(f"Published Messgae: {topic_msg}")
            return sns_msgid


    def process_sqs_to_sns(self, messages):
        logger.info(f"Processing {len(messages)} messages")
        success_ids = [self.process_message(message) for message in messages]
        delete_sqs_mgs_list = self.map_target_successes_to_source_sqs_delete_list(messages, success_ids)
        self.delete_sqs_batch_message(delete_sqs_mgs_list, SOURCESQSURL)
        logger.info(f"Suceessfully Deleted SQS Message: {delete_sqs_mgs_list}")
        logger.info("Processing Completed....")
