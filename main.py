import boto3
import string
import random
import requests
from typing import Tuple
from time import sleep, time

# basic constants for Seagate Lyve APIs
AuthEndpoint = "https://auth.lyve.seagate.com"
ApiEndpoint = "https://api.lyvecloud.seagate.com"

def get_random_string(length) -> str:
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str

def authenticate(accountId: str, clientId: str, clientSecret: str) -> str:
    # authenticate with Seagate Lyve
    request = {
        "accountId": accountId,
        "accessKey": clientId,
        "secret": clientSecret,
    }
    response = requests.post(f"{ApiEndpoint}/v2/auth/token", json=request)

    if response.status_code != 200:
        raise Exception(f"authentication failed: {response.status_code} => {response.text}")

    print(f"successfully authenticated")
    return response.json()["token"]

def create_permission(accessToken: str, prefix: str) -> str:
    # create a permission for the future service account
    request = {
        "name": prefix,
        "description": prefix,
        "type": "bucket-prefix",
        "actions": "all-operations",
        "prefix": prefix,
    }
    response = requests.post(
        f"{ApiEndpoint}/v2/permissions",
        json=request,
        headers={"Authorization": f"Bearer {accessToken}",},
    )

    if response.status_code != 200:
        raise Exception(f"create permission failed: {response.status_code} => {response.text}")

    permissionId = response.json()["id"]
    print(f"successfully created permission for [{prefixed}]: {permissionId}")
    return permissionId

def create_service_account(accountId: str, clientId: str, clientSecret: str, prefix: str) -> Tuple[str, str]:
    # create a Seagate Lyve service account

    # authenticate with Seagate Lyve
    accessToken = authenticate(accountId, clientId, clientSecret)

    # create a permission for the future service account
    permissionId = create_permission(accessToken, prefix)

    # create a service account with this permission
    request = {
        "name": prefix,
        "description": f"Service account for {prefix}",
        "permissions": [permissionId,],
    }
    response = requests.post(
        f"{ApiEndpoint}/v2/service-accounts",
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
accountId = ""
clientId = ""
accessSecret = ""

if accountId == "" :
    accountId = input("Enter Seagate Lyve accountId: ")

if clientId == "" :
    clientId = input("Enter Seagate Lyve accessKey: ")

if accessSecret == "":
    accessSecret = input("Enter Seagate Lyve secret: ")

# create a Seagate Lyve service account
key, secret = create_service_account(accountId, clientId, accessSecret, prefix)

print(f"key: [{key}]; secret: [{secret}]")

# craete an S3 client
client = boto3.client("s3", region_name=region,  endpoint_url=s3_endpoint, aws_access_key_id=key, aws_secret_access_key=secret)

print(f"trying to create a bucket [{bucket_name}] at endpoint [{s3_endpoint}]")

t_start = time()
while True:
    # time to create a bucket at specified endpoint
    try:
        client.create_bucket(Bucket=bucket_name)
        break
    except:
        print("failed to create a bucket, sleeping...")
        sleep(1)
        continue

# calculating the time it took
t_end = time() - t_start

# only possible to see the next message if bucket was successfully created
print(f"bucket successfully created in [{t_end:.2f} sec]")

# delete the bucket
client.delete_bucket(Bucket=bucket_name)