import os
import sys

CWD = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, CWD)

from main import *


def handler(event, context):
    logger.info("Processing Started....")
    messages = event["Records"]
    process_sqs_to_sns(messages)
