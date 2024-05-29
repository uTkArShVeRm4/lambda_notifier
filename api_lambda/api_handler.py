import json
import os

import boto3

dynamodb = boto3.resource("dynamodb")
sns_client = boto3.client("sns")

table = dynamodb.Table(os.environ["TABLE_NAME"])
topic_arn = os.environ["TOPIC_ARN"]


def handler(event, context):
    body = json.loads(event["body"])
    name = body.get("name")
    url = body.get("url")
    email = body.get("email")
    phone_number = body.get("phone_number")

    if not name or not url or (not email and not phone_number):
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "message": "Missing required parameters 'name', 'url', and at least one of 'email' or 'phone_number'"
                }
            ),
        }

    params = {
        "name": name,
        "url": url,
        "email": email,
        "phone_number": phone_number,
    }

    # Add the entry to DynamoDB
    table.put_item(Item=params)

    if email:
        filter_policy = json.dumps({"my_email": [email]})
        sns_client.subscribe(
            TopicArn=topic_arn,
            Protocol="email",
            Endpoint=email,
            Attributes={"FilterPolicy": filter_policy},
        )
    if phone_number:
        filter_policy = json.dumps({"my_phone": [phone_number]})
        sns_client.subscribe(
            TopicArn=topic_arn,
            Protocol="sms",
            Endpoint=phone_number,
            Attributes={"FilterPolicy": filter_policy},
        )
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "URL added and user subscribed",
                "data": params,
            }
        ),
    }
