#!/usr/bin/env python3
"""
Author : Kevin Ritchey <kevin@fortysheep.com>
Date   : 2023-06-05
Purpose: Create an AMI of the current EC2 instance
"""

import logging
import datetime
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import requests


# --------------------------------------------------
def create_ami():
    """Create an AMI of the current EC2 instance"""

    try:
        today_date = datetime.date.today().isoformat()
        instance_id = requests.get(
            "http://169.254.169.254/latest/meta-data/instance-id").text
        logging.info("Instance ID: %s", instance_id)
        ec2_client = boto3.client("ec2")
        response = ec2_client.create_image(
            InstanceId=instance_id,
            Name="BestCaseInstance-" + today_date,
            Description="BestCaseInstance-" + today_date,
            NoReboot=False,
        )
        logging.info("Response: %s", response)
        return True
    except ClientError as client_error:
        logging.critical("Creating AMI failed: %s", client_error)
        return False
    
if __name__ == "__main__":
    create_ami()
