#!/usr/bin/env python3
"""
Author : Kevin Ritchey <kevin@fortysheep.com>
Date   : 2023-06-05
Purpose: Backup BestCase CLIENTS Directory
"""

import argparse
import subprocess
import os
import datetime
import logging
import json


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
        default="C:\BestCase\CLIENTS",
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
def compress_dir_7z(directory_path, output_file=None, debug=False, log_file=None):
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
        logging.critical(f"Directory '{directory_path}' does not exist.")
        return [False, None]

    if not os.path.isdir(directory_path):
        logging.critical(f"Path '{directory_path}' is not a directory.")
        return [False, None]

    # Set default output path to TEMP directory if not provided
    if output_file is None:
        import tempfile
        import datetime

        current_datetime = datetime.datetime.now()
        current_datetime_iso = current_datetime.isoformat()
        current_datetime_iso_modified = current_datetime_iso.replace(":", "_")
        temp_dir = tempfile.gettempdir()
        output_file = temp_dir + "\\CLIENTS_" + current_datetime_iso_modified + ".7z"

    try:
        # test if 7z is installed
        subprocess.run(["7z"], stdout=subprocess.DEVNULL, check=True)
    except FileNotFoundError:
        logging.critical("7z is not installed.")
        return [False, None]
    except subprocess.CalledProcessError:
        logging.critical("7z is not installed or is not working.")
        return [False, None]

    try:
        subprocess.run(
            [
                "7z",
                "a",  # Add files to archive
                output_file,
                directory_path,
                "-r",  # Recurse subdirectories
                "-mx=9",  # Set maximum compression level
                "-mmt=on",  # Use multithreading
            ],
            check=True,
        )
        return [True, output_file]
    except subprocess.CalledProcessError as e:
        logging.critical(f"Compression failed: {e}")
        return [False, None]


# --------------------------------------------------
def send_backup(output_file, s3_bucket, use_boto=False, debug=False, log_file=None):
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
        logging.error(f"File '{output_file}' does not exist.")
        return False

    if not os.path.isfile(output_file):
        logging.error(f"Path '{output_file}' is not a file.")
        return False

    if use_boto:
        try:
            import boto3

            s3 = boto3.resource("s3")
            s3.meta.client.upload_file(output_file, s3_bucket, output_file)
            return True
        except Exception as e:
            logging.critical(f"Sending backup via Boto3 failed: {e}")
            return False
    else:
        try:
            subprocess.run(["aws", "s3", "cp", output_file, s3_bucket], check=True)
            return True
        except subprocess.CalledProcessError as e:
            logging.critical(f"Sending backup via AWS CLI failed: {e}")
            return False


# --------------------------------------------------
def send_msg_SNS(
    message, recipient, use_boto=False, subject=None, debug=False, log_file=None
):
    """Sends a message to an SNS topic

    Uses the Boto3 library if available, else sends the message via AWS CLI.

    Args:
        use_boto (bool): Whether to use the Boto3 library (True) or the AWS CLI (False)
        message (str): The message to send.
        subject (str): The subject line.
        recipient (str): The SNS topic ARN to send the message to.
        debug (bool): Whether to print debug messages.
        log_file (str): The path to the log file.

    Returns:
        bool: True if sending to the SNS topic was sent successfully, False otherwise.
    """

    if subject is None:
        subject = "Unknown error, please check logs."

    if use_boto:
        try:
            import boto3

            sns = boto3.client("sns")
            sns.publish(TopicArn=recipient, Message=message, Subject=subject)
            return True
        except Exception as e:
            logging.critical(f"Sending message via Boto3 to SNS topic failed: {e}")
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
        except subprocess.CalledProcessError as e:
            logging.critical(f"Sending message via AWS CLI to SNS topic failed: {e}")
            return False


# --------------------------------------------------
def test_boto3(debug=False, log_file=None):
    """Tests if boto3 is installed"""

    try:
        # test if boto3 is installed
        import boto3

        return True
    except ModuleNotFoundError:
        logging.error("boto3 is not installed.")
        return False


# --------------------------------------------------
def test_awsc(debug=False, log_file=None):
    """Tests if aws cli is installed"""

    try:
        # test if aws is installed
        subprocess.run(["aws"], stdout=subprocess.DEVNULL, check=True)
        return True
    except FileNotFoundError:
        logging.error("aws is not installed.")
        return False
    except subprocess.CalledProcessError:
        logging.error("aws is not installed.")
        return False


# --------------------------------------------------
def prune_backups(s3_bucket, days=7, use_boto=False, debug=False, log_file=None):
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
            import boto3

            s3 = boto3.resource("s3")
            bucket = s3.Bucket(s3_bucket)
            for obj in bucket.objects.all():
                if obj.last_modified < datetime.datetime.now(
                    datetime.timezone.utc
                ) - datetime.timedelta(days=days):
                    obj.delete()
            return True
        except Exception as e:
            logging.critical(f"Pruning via Boto3 failed: {e}")
            return False
    else:
        try:
            # create list of backups to delete
            backups_to_keep = []
            bucket_name = s3_bucket.replace("s3://", "")
            command = f"aws s3 ls s3://{bucket_name} --recursive"
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
        except subprocess.CalledProcessError as e:
            logging.critical(f"Pruning via AWS CLI failed: {e}")
            return False


# --------------------------------------------------
def main():
    """Do the heavy lifting of backing up the BestCase CLIENTS directory
    to an S3 bucket"""

    main_start_time = datetime.datetime.now()
    args = get_args()
    config_file = args.config_file

    use_boto = False
    use_aws = False

    if debug:
        logging.debug(f'CLIENTS directory = "{directory_path}"')
        logging.debug(f'CLIENTS directory = "{directory_path}"')
        logging.debug(f'S3 backup bucket = "{s3_bucket}"')
        logging.debug(f'Debug = "{debug}"')
        logging.debug(f'Config file = "{config_file}"')

    # Use config file if provided, else use command line arguments
    if config_file is not None:
        config = json.load(config_file)
        directory_path = config["clients"]
        s3_bucket = config["s3"]
        debug = config["debug"]
    else:
        directory_path = args.clients
        s3_bucket = args.s3
        debug = args.debug

    # Exit if S3 bucket is 's3://my-bestcase-backup'
    if s3_bucket == "s3://my-bestcase-backup":
        logging.warning("S3 bucket is set to 's3://my-bestcase-backup', exiting.")
        logging.warning("Please set the S3 bucket to your own bucket.")
        return False

    # Define location of log file
    if log_file == "None":
        import tempfile

        temp_dir = tempfile.gettempdir()
        log_file = temp_dir + "\\BestCaseBackup.log"

    logging.basicConfig(filename=log_file, encoding="utf-8", level=logging.DEBUG)
    if debug:
        logging.basicConfig(
            format="%(asctime)s %(levelname)s: %(message)s", level=logging.DEBUG
        )
    else:
        logging.basicConfig(
            format="%(asctime)s %(levelname)s: %(message)s", level=logging.INFO
        )
    log_start_time = datetime.datetime.now()
    logging.info(f"Log started at {log_start_time}")

    # if we are using boto3, test if boto3 is installed otherwise
    # test if aws cli is installed - Exit if neither is installed
    use_boto = test_boto3(debug, log_file)
    if use_boto == False:
        use_aws = test_awsc(debug, log_file)
        if use_aws == False:
            logging.error("No AWS CLI or boto3 found, exiting.")
            return False

    # Compress the BestCase CLIENTS directory
    [compress_success, output_file] = compress_dir_7z(
        directory_path, output_file=None, debug=debug, log_file=log_file
    )

    if not compress_success:
        logging.error("Compression failed, exiting now.")
        return False
    else:
        logging.info(f"Compressed file: {output_file}")
        try:
            copy_success = send_backup(
                output_file, s3_bucket, use_boto, debug, log_file
            )
            if copy_success:
                logging.info("Backup sent successfully.")
                return True
            else:
                logging.warning("Sending backup failed w/o an exception code.")
                return False
        except Exception as e:
            logging.critical(f"Sending backup failed: {e}")
            return False
        finally:
            os.remove(output_file)
            main_end_time = datetime.datetime.now()
            elapsed_time = main_end_time - main_start_time
            logging.info(f"Elapsed time: {elapsed_time}")


# --------------------------------------------------
if __name__ == "__main__":
    start_time = datetime.datetime.now()
    success = main()
    end_time = datetime.datetime.now()
    elapsed_time = end_time - start_time
    logging.info(f"Elapsed time: {elapsed_time}") if success else None
