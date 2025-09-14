import my_stack as core
import aws_cdk.assertions as assertions

from my_stack.aws_cdk_stack import AwsCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in aws_cdk/aws_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = AwsCdkStack(app, "aws-cdk")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
