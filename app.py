import os
from aws_cdk import App, Environment, LegacyStackSynthesizer
from my_stack.aws_cdk_stack import AwsCdkStack

app = App()

# Usar LegacyStackSynthesizer para evitar bootstrap completamente
AwsCdkStack(app, "AwsCdkStack",
    synthesizer=LegacyStackSynthesizer(),
    env=Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT", "045517588521"),
        region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1")
    )
)

app.synth()
