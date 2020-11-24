# 
Python Function to send email reminders to IAM users on Access Keys age.
If You have many IAM users or Multiple Aws accounts, its always boring to highlight the user access keys older than specific days (i.e 90 days). So, I wrote some code to doing it automatically leveraging AWS Lambda. 

# Permissions Required 
Lambda function will need to have access to some sets of permissions to perform its taks. For that, Create a custom role and attach the managed policy ***AWSLambdaBasicExecutionRole***. Other than this, create a custom inline policy with this permissions:
```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "ses:SendEmail",
                "iam:ListAccessKeys",
                "iam:ListUserTags"
            ],
            "Resource": [
                "arn:aws:iam::<ACCOUNT_ID>:user/*",
                "arn:aws:ses:eu-central-1:<ACCOUNT_ID>:identity/*"
            ]
        },
        {
            "Sid": "VisualEditor1",
            "Effect": "Allow",
            "Action": "iam:ListUsers",
            "Resource": "*"
        }
    ]
}
```
# Set Up SES 
Lambda will make use of AWS SES Service to send emails, so set up and verify domain in SES. 
