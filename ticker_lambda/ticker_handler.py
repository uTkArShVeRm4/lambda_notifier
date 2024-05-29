import json
import os

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])
sqs = boto3.client("sqs")


def handler(event, context):
    # Retrieve the queue URL using the queue name
    QUEUE_URL = os.environ["QUEUE_URL"]

    # Scan the DynamoDB table to get all items
    res = table.scan()
    items = res["Items"]

    # Send each item to the SQS queue
    for item in items:
        sqs.send_message(
            QueueUrl=QUEUE_URL,
            DelaySeconds=10,
            MessageBody=json.dumps(
                {
                    "url": item["url"],
                    "name": item["name"],
                    "email": item.get("email"),
                    "phone_number": item.get("phone_number"),
                }
            ),
        )

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Messages sent to SQS successfully."}),
    }
