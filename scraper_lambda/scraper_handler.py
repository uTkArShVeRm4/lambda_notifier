import json
import os

import boto3
import requests
from bs4 import BeautifulSoup

sqs = boto3.client("sqs")
sns_client = boto3.client("sns")
topic_arn = os.environ["TOPIC_ARN"]

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["TABLE_NAME"])


def handler(event, context):

    # Check if any messages are received
    for message in event["Records"]:
        body = message["body"]
        message_attributes = message.get("MessageAttributes", {})

        # Parse the message body to get the URL
        body_data = json.loads(body)
        url = body_data.get("url")
        name = body_data.get("name")
        email = body_data.get("email")
        phone_number = body_data.get("phone_number")

        if url:
            # Fetch the webpage content
            page_response = requests.get(url)

            # Check if the request was successful
            if page_response.status_code == 200:
                # Parse the HTML content using BeautifulSoup
                soup = BeautifulSoup(page_response.content, "html.parser")

                # Get the text content of the page
                page_text = soup.get_text()

                # Check if 'out of stock' is in the text
                if "out of stock" in page_text.lower():
                    print("The phrase 'out of stock' is present on the page.")
                    sns_client.publish(
                        TopicArn=topic_arn,
                        Message=json.dumps(
                            {
                                "sms": f"Your item {name} is in stock.",
                                "email": f"Your item {name} is in stock.",
                            }
                        ),
                        MessageStructure="json",
                        MessageAttribute={
                            "my_email": {"DataType": "String", "Value": email},
                            "my_phone": {
                                "DataType": "String",
                                "Value": phone_number,
                            },
                        },
                    )
                    table.delete(Key={"name": name, "url": url})
                else:
                    print("The phrase 'out of stock' is not present on the page.")

            else:
                print(
                    f"Failed to retrieve the page. Status code: {page_response.status_code}"
                )

            # Delete the processed message from the queue
            sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=receipt_handle)
        else:
            print("No URL found in the message body.")
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Website scraped successfully"}),
    }


# Test the handler function
if __name__ == "__main__":
    handler(None, None)
