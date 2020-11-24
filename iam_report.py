from collections import defaultdict
from datetime import datetime, timezone
import logging
import boto3
from botocore.exceptions import ClientError


# How many days before sending alerts about the key age
ALERT_AFTER_N_DAYS = 90
# How ofter we have set the cron to run the Lambda
SEND_EVERY_N_DAYS = 3
# From Email Address
SES_SENDER_EMAIL_ADDRESS = 'support@example.com'
# SES Region
SES_REGION_NAME = 'us-west-2'

iam_client = boto3.client('iam')    
ses_client = boto3.client('ses', region_name=SES_REGION_NAME)

# Helper function to choose if a key owner should be notified today
def is_key_interesting(key):
    if key['Status'] != 'Active':
        return False
    
    elapsed_days = (datetime.now(timezone.utc) - key['CreateDate']).days

    if elapsed_days < ALERT_AFTER_N_DAYS:
        return False
    
    return True
    
def send_notification(email, keys, account_id):
    email_text = f'''Dear {keys[0]['UserName']},\r\n
This is an automatic reminder to rotate your AWS Access Keys at least every {ALERT_AFTER_N_DAYS} days.\r

At the moment, you have {len(keys)} key(s) on the account {account_id} that have been created more than {ALERT_AFTER_N_DAYS} days ago:
'''
    for key in keys:
        email_text += f"- {key['AccessKeyId']} was created on {key['CreateDate']} ({(datetime.now(timezone.utc) - key['CreateDate']).days} days ago)\r\r"
    
    email_text += f"""
To learn how to rotate your AWS Access Key, please read the official guide at https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html#Using_RotateAccessKey\r
If you have any question, please don't hesitate to contact the Support Team at support@example.com.\r

This automatic reminder will be sent again in {SEND_EVERY_N_DAYS} days, if the key(s) will not be rotated.\r

Regards,\r\n
Your lovely Support Team
"""
    
    try:
        ses_response = ses_client.send_email(
            Destination={'ToAddresses': [email]},
            Message={
                'Body': {'Text': {'Charset': 'UTF-8', 'Data': email_text}},
                'Subject': {'Charset': 'UTF-8',
                            'Data': f'Remember to rotate your AWS Keys on {account_id}!'}
            },
            Source=SES_SENDER_EMAIL_ADDRESS
        )
    except ClientError as e:
        logging.error(e.response['Error']['Message'])
    else:
        logging.info(f'Notification email sent successfully to {email}! Message ID: {ses_response["MessageId"]}')

def lambda_handler(event, context):
    users = []
    is_truncated = True
    marker = None
    

    while is_truncated:
        # This strange syntax is here because `list_users` doesn't accept an 
        # invalid Marker argument, so we specify it only if it is not None
        response = iam_client.list_users(**{k: v for k, v in (dict(Marker=marker)).items() if v is not None})
        users.extend(response['Users'])
        is_truncated = response['IsTruncated']
        marker = response.get('Marker', None)
    
 
    filtered_users = list(filter(lambda u: u.get('PasswordLastUsed'), users))
    interesting_keys = []
    
    for user in filtered_users:
        response = iam_client.list_access_keys(UserName=user['UserName'])
        access_keys = response['AccessKeyMetadata']
        interesting_keys.extend(list(filter(lambda k: is_key_interesting(k), access_keys)))
    
    interesting_keys_grouped_by_user = defaultdict(list)
    for key in interesting_keys:
        interesting_keys_grouped_by_user[key['UserName']].append(key)

    for user in interesting_keys_grouped_by_user.values():
        try:
            tags = iam_client.list_user_tags(UserName = user[0]['UserName'])
            if tags['Tags']:    
                email_id = None
                for tag in tags['Tags']:
                    if tag['Key'] == 'emailid':
                        email_id = tag['Value']
                if email_id == None:
                    print('No Email Found for ' + user[0]['UserName'] )
                else: 
                    print('Found Email ID: ' + email_id )
            else: 
                print('Missing tags for ' + user[0]['UserName'])
            if email_id:
                print('Sending email')
                send_notification(email_id, user, context.invoked_function_arn.split(":")[4])
        except ClientError:
            logging.exception('message')
