#!/usr/bin/env python3
"""
Author : Kevin Ritchey <kevin@fortysheep.com>
Date   : 2023-06-05
Purpose: Backup BestCase CLIENTS Directory
"""

import argparse
import subprocess
import os
import logging
import json
import tempfile
import datetime
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
import psutil
import requests


# --------------------------------------------------
def get_args():
    """Get command-line arguments"""

    parser = argparse.ArgumentParser(
        description="Backup BestCase CLIENTS Directory",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-c",
        "--clients",
        help="BestCase CLIENTS Directory",
        metavar="str",
        type=str,
        required=False,
        default="C:\\BestCase\\CLIENTS",
    )

    parser.add_argument(
        "-s",
        "--s3",
        help="S3 bucket full name",
        metavar="str",
        type=str,
        required=False,
        default="s3://my-bestcase-backup",
    )

    parser.add_argument(
        "-d",
        "--debug",
        help="Whether to run in Debug mode",
        required=False,
        action="store_false",
    )

    parser.add_argument(
        "-f",
        "--config-file",
        help="Path to config file",
        metavar="FILE",
        required=False,
        type=argparse.FileType("r"),
    )

    return parser.parse_args()


# --------------------------------------------------
def compress_dir_7z(directory_path, output_file=None):
    """Compresses a directory using 7zip.

    Args:
        directory_path (str): The path to the directory to be compressed.
        output_file (str): The path to save the compressed file.
        debug (bool): Whether to print debug messages.
        log_file (str): The path to the log file.

    Returns:
        a list comprising a
            bool: True if compression was successful, False otherwise.
            str: The path to the compressed file.
    """

    if not os.path.exists(directory_path):
        logging.critical("Directory '%s' does not exist.", directory_path)
        return [False, None]

    if not os.path.isdir(directory_path):
        logging.critical("Path '%s' is not a directory.", directory_path)
        return [False, None]

    # Set default output path to TEMP directory if not provided
    if output_file is None:
        current_datetime = datetime.datetime.now()
        current_datetime_iso = current_datetime.isoformat()
        current_datetime_iso_modified = current_datetime_iso.replace(":", "_")
        temp_dir = tempfile.gettempdir()
        output_file = temp_dir + "\\CLIENTS_" + current_datetime_iso_modified + ".7z"

    try:
        # test if 7z is installed
        subprocess.run(["7z"], stdout=subprocess.DEVNULL, check=True)
        logging.info("7z is installed.")
    except FileNotFoundError:
        logging.critical("7z is not installed.")
        return [False, None]
    except subprocess.CalledProcessError:
        logging.critical("7z is not installed or is not working.")
        return [False, None]

    clients_path = directory_path + "\\CLIENTS\\"  # 7z needs the trailing slash
    try:
        subprocess.run(
            [
                "7z",
                "a",  # Add files to archive
                output_file,
                clients_path,
                "-r",  # Recurse subdirectories
                "-mx=9",  # Set maximum compression level
                "-mmt=on",  # Use multithreading
            ],
            check=True,
        )
        return [True, output_file]
    except subprocess.CalledProcessError as called_error:
        logging.critical("Compression failed: %s", called_error)
        return [False, None]


# --------------------------------------------------
def send_backup(output_file, s3_bucket, use_boto=False):
    """Sends a backup file to an S3 bucket.

    Args:
        output_path (str): The path to the backup file.
        s3_bucket (str): The name of the S3 bucket to send the backup to.
        use_boto (bool): Whether to use the Boto3 library (True) or the AWS CLI (False)
        debug (bool): Whether to print debug messages.
        log_file (str): The path to the log file.

    Returns:
        bool: True if the backup was sent successfully, False otherwise.
    """

    if not os.path.exists(output_file):
        logging.error("File '%s' does not exist.", output_file)
        return False

    if not os.path.isfile(output_file):
        logging.error("Path '%s' is not a file.", output_file)
        return False

    if use_boto:
        try:
            s3_bucket = s3_bucket.replace("s3://", "")
            logging.info("Sending %s backup via Boto3.", output_file)
            output_file_name = Path(output_file).name
            s3_client = boto3.client("s3")
            response = s3_client.upload_file(output_file, s3_bucket, output_file_name)
            logging.info("Response: %s", response)
            return True
        except ClientError as s3_error:
            logging.critical("Sending backup via Boto3 failed: %s", s3_error)
            return False
    else:
        try:
            subprocess.run(["aws", "s3", "cp", output_file, s3_bucket], check=True)
            return True
        except subprocess.CalledProcessError as called_error:
            logging.critical("Sending backup via AWS CLI failed: %s", called_error)
            return False


# --------------------------------------------------
def send_msg_sns(message, recipient, use_boto=False, subject=None):
    """Sends a message to an SNS topic

    Uses the Boto3 library if available, else sends the message via AWS CLI.

    Args:
        use_boto (bool): Whether to use the Boto3 library (True) or the AWS CLI (False)
        message (str): The message to send.
        subject (str): The subject line.
        recipient (str): The SNS topic ARN to send the message to.

    Returns:
        bool: True if sending to the SNS topic was sent successfully, False otherwise.
    """

    if subject is None:
        subject = "Unknown error, please check logs."

    if use_boto:
        try:
            sns = boto3.client("sns")
            sns.publish(TopicArn=recipient, Message=message, Subject=subject)
            return True
        except ClientError as client_error:
            logging.critical(
                "Sending message via Boto3 to SNS topic failed: %s", client_error
            )
            return False
    else:
        try:
            subprocess.run(
                [
                    "aws",
                    "sns",
                    "publish",
                    "--topic-arn",
                    recipient,
                    "--message",
                    message,
                    "--subject",
                    subject,
                ],
                check=True,
            )
            return True
        except subprocess.CalledProcessError as called_error:
            logging.critical(
                "Sending message via AWS CLI to SNS topic failed: %s", called_error
            )
            return False


# --------------------------------------------------
def prune_backups(s3_bucket, days=7, use_boto=False):
    """Prunes old backups from an S3 bucket.

    Args:
        s3_bucket (str): The name of the S3 bucket to prune.
        days (int): The number of days to keep backups for.
        use_boto (bool): Whether to use the Boto3 library (True) or the AWS CLI (False)
        debug (bool): Whether to print debug messages.
        log_file (str): The path to the log file.

    Returns:
        bool: True if pruning was successful, False otherwise.
    """

    if use_boto:
        try:
            s3_client = boto3.resource("s3")
            s3_bucket = s3_bucket.replace("s3://", "")
            bucket = s3_client.Bucket(s3_bucket)
            for obj in bucket.objects.all():
                if obj.last_modified < datetime.datetime.now(
                    datetime.timezone.utc
                ) - datetime.timedelta(days=days):
                    print(obj.key)
                    obj.delete()
            return True
        except ClientError as client_error:
            logging.critical("Pruning via Boto3 failed: %s", client_error)
            return False
    else:
        try:
            # create list of backups to delete
            # backups_to_keep = []
            # bucket_name = s3_bucket.replace("s3://", "")
            command = f"aws s3 ls {s3_bucket} --recursive"
            output = subprocess.check_output(command, shell=True).decode("utf-8")
            objects = []

            # Process the output
            lines = output.strip().split("\n")
            for line in lines:
                parts = line.split()
                if len(parts) > 3:
                    item = [parts[0], parts[2]]
                    objects.append(item)

            subprocess.run(
                [
                    "aws",
                    "s3",
                    "rm",
                    s3_bucket,
                    "--recursive",
                    "--exclude",
                    "*",
                    "--include",
                    f"*{days}*.7z",
                ],
                check=True,
            )
            return True
        except subprocess.CalledProcessError as called_error:
            logging.critical("Pruning via AWS CLI failed: %s", called_error)
            return False


# --------------------------------------------------
def close_processes_by_name(process_name):
    for process in psutil.process_iter(['name']):
        if process.info['name'] == process_name:
            process.kill()


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
    

# --------------------------------------------------
def main():
    """Do the heavy lifting of backing up the BestCase CLIENTS directory
    to an S3 bucket"""

    args = get_args()
    config_file = args.config_file

    # Use config file if provided, else use command line arguments
    if config_file is not None:
        config = json.load(config_file)
        directory_path = config["best_case_dir"]
        s3_bucket = config["s3_bucket"]
        debug = config["debug_mode"]
        use_boto3 = config["use_boto3"]
        topic_arn = config["topic_arn"]
    else:
        logging.critical("No config file provided, exiting.")
        return False

    # Exit if S3 bucket is 's3://my-bestcase-backup'
    if s3_bucket == "s3://my-bestcase-backup":
        logging.warning("S3 bucket is set to 's3://my-bestcase-backup', exiting.")
        logging.warning("Please set the S3 bucket to your own bucket.")
        return False

    # Define location of log file
    log_file = tempfile.gettempdir() + "\\BestCaseBackup"

    # if log file is too big, delete it
    if os.path.exists(log_file):
        if os.path.getsize(log_file) > 1000000:
            os.remove(log_file)

    # Set logging level and start logging
    if debug:
        logging.basicConfig(
            filename=log_file,
            encoding="utf-8",
            format="%(asctime)s %(levelname)s: %(message)s",
            level=logging.DEBUG,
        )
    else:
        logging.basicConfig(
            filename=log_file,
            encoding="utf-8",
            format="%(asctime)s %(levelname)s: %(message)s",
            level=logging.INFO,
        )
    logging.info("Log started at %s", datetime.datetime.now())
    
    # Compress the BestCase CLIENTS directory
    logging.info("Compressing directory: %s", directory_path)
    
    # close all BestCase processes
    close_processes_by_name('WinBFS.EXE')
    [compress_success, output_file] = compress_dir_7z(directory_path, output_file=None)

    if not compress_success:
        logging.error("Compression failed, exiting now.")
        return False

    logging.info("Compressed file: %s", output_file)

    # Send the backup to the S3 bucket
    try:
        copy_success = send_backup(output_file, s3_bucket, use_boto3)
        if not copy_success:
            logging.warning("Sending backup failed w/o an exception code.")
            message = "BestCase backup failed"
            subject = "BestCase backup failed"
            try:
                send_msg_sns(message, topic_arn, use_boto=True, subject=subject)
            except Exception as sns_error:
                logging.warning("Sending message to SNS topic failed: %s", sns_error)
            return False
        logging.info("Backup sent successfully.")
        try:
            prune_backups(s3_bucket, days=7, use_boto=use_boto3)
            logging.info("Old backups pruned successfully.")
        except Exception as prune_error:
            logging.warning("Pruning backups failed: %s", prune_error)
        return True
    except ClientError as send_error:
        logging.critical("Sending backup failed: %s", send_error)
        return False
    finally:
        logging.info("Removing compressed file: %s", output_file)
        os.remove(output_file)


# --------------------------------------------------
if __name__ == "__main__":
    start_time = datetime.datetime.now()
    main()
    end_time = datetime.datetime.now()
    elapsed_time = end_time - start_time
    logging.info("Elapsed time: %s", elapsed_time)
    """ 
    Create an AMI of the current EC2 instance if it's Sunday 
    This will stop the instance, create the AMI, and then start the instance
    hence the need to run this after the backup is complete
    """
    if datetime.date.today().weekday() == 6:
        create_ami()