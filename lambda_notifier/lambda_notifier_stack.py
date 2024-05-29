from aws_cdk import Stack  # Duration,; aws_sqs as sqs,
from aws_cdk import (
    Duration,
    aws_apigateway,
    aws_dynamodb,
    aws_events,
    aws_events_targets,
    aws_iam,
    aws_lambda,
    aws_lambda_event_sources,
    aws_sns,
    aws_sqs,
)
from constructs import Construct


class LambdaNotifierStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create DynamoDB table
        ddb = aws_dynamodb.Table(
            self,
            "UrlsTable",
            partition_key=aws_dynamodb.Attribute(
                name="name", type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(
                name="url", type=aws_dynamodb.AttributeType.STRING
            ),
        )

        ddb.add_global_secondary_index(
            index_name="EmailIndex",
            partition_key=aws_dynamodb.Attribute(
                name="email", type=aws_dynamodb.AttributeType.STRING
            ),
            sort_key=aws_dynamodb.Attribute(
                name="phone_number", type=aws_dynamodb.AttributeType.STRING
            ),
            projection_type=aws_dynamodb.ProjectionType.ALL,
        )

        # Create SNS topic
        topic = aws_sns.Topic(self, "SubscriptionTopic")

        # Creating an API to add urls and email subscription
        gateway = aws_apigateway.RestApi(
            self,
            "Subscribe",
            rest_api_name="Subscribe",
            description="Subscribe to receiving notification about items coming back in stock.",
        )

        # Add subscription route
        subscription_resource = gateway.root.add_resource("subscribe")

        # Create API lambda
        api_lambda = aws_lambda.Function(
            self,
            "ApiLambda",
            handler="api_handler.handler",
            code=aws_lambda.Code.from_asset("api_lambda"),
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            environment={
                "TABLE_NAME": ddb.table_name,
                "TOPIC_ARN": topic.topic_arn,
            },
        )

        # Grant permissions
        ddb.grant_read_write_data(api_lambda)
        topic.grant_publish(api_lambda)
        api_lambda.add_to_role_policy(
            aws_iam.PolicyStatement(
                actions=["sns:Subscribe", "sns:Publish"], resources=[topic.topic_arn]
            )
        )

        # Add API lambda to route
        subscription_resource.add_method(
            "POST",
            aws_apigateway.LambdaIntegration(api_lambda),
            authorization_type=aws_apigateway.AuthorizationType.NONE,
        )

        # Create Cloudwatch event rule
        ticker = aws_events.Rule(
            self, "Ticker", schedule=aws_events.Schedule.rate(Duration.minutes(5))
        )

        # Create Ticker lambda
        init_lambda = aws_lambda.Function(
            self,
            "InitLambda",
            handler="ticker_handler.handler",
            code=aws_lambda.Code.from_asset("ticker_lambda"),
            runtime=aws_lambda.Runtime.PYTHON_3_12,
        )

        # Add tickers target to be init_lambda
        ticker.add_target(aws_events_targets.LambdaFunction(init_lambda))

        # Create SQS event queue
        queue = aws_sqs.Queue(
            self, "ScrapeQueue", visibility_timeout=Duration.seconds(300)
        )

        # Create scraper lambda
        scraper_lambda = aws_lambda.Function(
            self,
            "ScraperLambda",
            handler="scraper_handler.handler",
            code=aws_lambda.Code.from_asset("scraper_lambda"),
            runtime=aws_lambda.Runtime.PYTHON_3_12,
        )

        # Add scraper lambdas event source to be queue
        scraper_lambda.add_event_source(aws_lambda_event_sources.SqsEventSource(queue))
