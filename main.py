import boto3
import string
import random
import requests
from typing import Tuple
from time import sleep

# basic constants for Seagate Lyve APIs
AuthEndpoint = "https://auth.lyve.seagate.com"
ApiEndpoint = "https://api.lyvecloud.seagate.com"

def get_random_string(length) -> str:
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str

def authenticate(clientId: str, clientSecret: str) -> str:
    # authenticate with Seagate Lyve
    request = {
        "client_id": clientId,
        "client_secret": clientSecret,
        "audience": "https://lyvecloud/customer/api",
        "grant_type": "client_credentials",
    }
    response = requests.post(f"{AuthEndpoint}/oauth/token", json=request)

    print("successfully authenticated")
    return response.json()["access_token"]

def create_permission(accessToken: str, prefix: str) -> str:
    # create a permission for the future service account
    prefixed = f"{prefix}*"
    request = {
        "name": prefix,
        "description": prefix,
        "actions": "all-operations",
        "buckets": [prefixed],
    }
    response = requests.put(
        f"{ApiEndpoint}/v1/permission",
        json=request,
        headers={"Authorization": f"Bearer {accessToken}",},
    )

    permissionId = response.json()["id"]
    print(f"successfully created permission for [{prefixed}]: {permissionId}")
    return permissionId

def create_service_account(clientId: str, clientSecret: str, prefix: str) -> Tuple[str, str]:
    # create a Seagate Lyve service account

    # authenticate with Seagate Lyve
    accessToken = authenticate(clientId, clientSecret)

    # create a permission for the future service account
    permissionId = create_permission(accessToken, prefix)

    # create a service account with this permission
    request = {
        "name": prefix,
        "description": f"Service account for {prefix}",
        "permissions": [permissionId,],
    }
    response = requests.put(
        f"{ApiEndpoint}/v1/service-account",
        json=request,
        headers={"Authorization": f"Bearer {accessToken}",},
    )
    print(f"successfully created service account [{prefix}]")
    return response.json()["access_key"], response.json()["access_secret"]


# defining the key variables
region = "us-west-1"
prefix = f"pf-{get_random_string(8)}"
s3_endpoint = f"https://s3.{region}.lyvecloud.seagate.com"
bucket_name = f"{prefix}-{region}"

# might be provided right here, or will be requested via input
clientId = ""
accessSecret = ""

if clientId == "" :
    clientId = input("Enter Seagate Lyve clientId: ")

if accessSecret == "":
    accessSecret = input("Enter Seagate Lyve secret: ")

# create a Seagate Lyve service account
key, secret = create_service_account(clientId, accessSecret, prefix)

print(f"key: [{key}]; secret: [{secret}]")

# craete an S3 client
client = boto3.client("s3", region_name=region,  endpoint_url=s3_endpoint, aws_access_key_id=key, aws_secret_access_key=secret)

# sleeping 5 seconds, as requested by Seagate Lyve engineers
sleep(5)

# time to create a bucket at specified endpoint
print(f"trying to create a bucket [{bucket_name}] at endpoint [{s3_endpoint}]")
client.create_bucket(Bucket=bucket_name)


# only possible to see next message at us-east-1
print("bucket successfully created")