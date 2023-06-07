#!/usr/bin/env python3
"""
Author : Kevin Ritchey <kevin@fortysheep.com>
Date   : 2023-06-07
Purpose: creates a config file
"""

import json
import os
import sys
import subprocess
import logging


# --------------------------------------------------
def test_whether_boto3_is_installed(doc_site):
    """Test whether boto3 is installed"""
    try:
        import boto3
    except ImportError:
        logging.warning("ERROR: boto3 is not installed")
        logging.warning("Please see %s for installation instructions", doc_site)

        return False

    return True


# --------------------------------------------------
def install_boto3():
    """Install boto3"""
    try:
        subprocess.run(
            ["pip", "install", "boto3"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError as called_error:
        logging.warning("ERROR: boto3 could not be installed")
        logging.warning("ERROR: %s", called_error)
        logging.warning("Please install boto3 manually")
        return False

    return True  # boto3 was installed


# --------------------------------------------------
def test_aws_cli_is_installed():
    """Test whether AWS CLI executable is installed and in my PATH"""
    try:
        subprocess.run(
            ["aws", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError as called_error:
        logging.warning("ERROR: AWS CLI is not installed")
        logging.warning("ERROR: %s", called_error)
        return False

    return True


# --------------------------------------------------
def test_aws_cli_is_configured(doc_site):
    """Test whether AWS CLI is configured"""
    try:
        # call subprocess but don't capture output
        subprocess.run(
            ["aws", "s3", "ls"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError as called_error:
        logging.warning("ERROR: AWS CLI is not configured")
        logging.warning("ERROR: %s", called_error)
        logging.warning("Please see %s for configuration instructions", doc_site)
        return False

    return True


# --------------------------------------------------
def test_best_case_dir(best_case_dir):
    """Test if the Best Case directory exists"""
    if not os.path.isdir(best_case_dir):
        logging.critical("ERROR: '%s' is not a directory", best_case_dir)
        logging.warning("Please check your Best Case directory and try again")
        return False
    clients_dir = os.path.join(best_case_dir, "CLIENTS")
    if not os.path.isdir(clients_dir):
        logging.critical("ERROR: '%s' is not a directory", clients_dir)
        logging.warning("Please check your Best Case directory and try again")
        return False
    return True


# --------------------------------------------------
def new_s3_bucket(s3_bucket):
    """Prompt user to create a new S3 bucket"""
    try:
        subprocess.run(
            ["aws", "s3", "mb", s3_bucket],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError as called_error:
        logging.warning("ERROR: AWS S3 bucket '%s' could not be created", s3_bucket)
        logging.warning("ERROR: %s", called_error)
        logging.warning("Please choose a different name for your S3 bucket")
        return False

    return True


# --------------------------------------------------
def test_s3_bucket(s3_bucket):
    """Test if the S3 bucket exists or create S3 bucket"""
    try:
        # call subprocess but don't capture output
        subprocess.run(
            ["aws", "s3", "ls", s3_bucket],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError as called_error:
        logging.warning("ERROR: AWS S3 bucket '%s' does not exist", s3_bucket)
        logging.warning("ERROR: %s", called_error)
        logging.warning("Please create the S3 bucket or specify a different S3 bucket")
        return False

    return True


# --------------------------------------------------
def create_config_file(use_boto3):
    """Create the config file"""
    config = {}

    # Prompt for Best Case installation directory
    best_case_dir_exists = False
    while not best_case_dir_exists:
        best_case_dir = input("Where is Best Case installed? E.g. C:\\BestCase: ")
        best_case_dir_exists = test_best_case_dir(best_case_dir)
    config["best_case_dir"] = best_case_dir

    # Prompt for AWS S3 bucket for backups
    test_s3_bucket_exists = False
    create_s3_bucket = False

    while not create_s3_bucket:
        do_create_s3_bucket = input(
            "Do you want to create an AWS S3 bucket for backups? (Y/N): "
        )
        if do_create_s3_bucket.lower() == "y":
            s3_bucket = input(
                "What do you want to call the AWS S3 bucket? E.g. my-bestcase-backups: "
            )
            create_s3_bucket = new_s3_bucket(s3_bucket)
        else:
            while not test_s3_bucket_exists:
                s3_bucket = input(
                    "What S3 bucket will you use to store your backups? E.g. s3://my-bc-backups: "
                )
                test_s3_bucket_exists = test_s3_bucket(s3_bucket)

    config["s3_bucket"] = s3_bucket

    # Prompt for DEBUG mode
    debug_mode = input("Do you want to run the script in DEBUG mode? (Y/N): ")
    config["debug_mode"] = debug_mode.lower() == "y"

    # Save use_bot3 to config file
    config["use_boto3"] = use_boto3

    # Save configuration to JSON file
    with open("config.json", "w", encoding="utf8") as file:
        json.dump(config, file, indent=4)

    logging.info("Config file created successfully.")


# --------------------------------------------------
def main():
    """Make a jazz noise here"""
    doc_site = (
        "https://boto3.amazonaws.com/v1/documentation/api/" +
        "latest/guide/quickstart.html#configuration"
    )
    windows_doc_site = (
        "https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-windows.html"
    )
    logging.basicConfig(format="%(levelname)s - %(message)s", level=logging.INFO)

    if not test_whether_boto3_is_installed(doc_site):
        logging.info("INFO: boto3 is not installed")
        input("Press Enter to install boto3")
        if not install_boto3():
            logging.error("ERROR: boto3 could not be installed")
            logging.error("ERROR: Please see %s for installation instructions", doc_site)
            input("Do you want to continue without installing boto3? (Y/N): ")
            if input.lower() == "y":
                use_boto3 = False
            else:
                logging.critical("ERROR: Will not continue without boto3")
                sys.exit(1)
        else:
            use_boto3 = True
    else:
        use_boto3 = True
    if not test_aws_cli_is_installed():
        logging.error("ERROR: AWS CLI is not installed and boto3 is not installed")
        logging.error(
            "ERROR: Please install AWS CLI. See %s for instructions.", windows_doc_site
        )
        sys.exit(1)
    if not test_aws_cli_is_configured(doc_site):
        logging.error("ERROR: AWS CLI is not configured")
        logging.error("ERROR: Please run 'aws configure' to configure AWS CLI")
        sys.exit(1)
    # Create the config file
    create_config_file(use_boto3)


# --------------------------------------------------
if __name__ == "__main__":
    main()
