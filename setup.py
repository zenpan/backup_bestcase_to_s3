#!/usr/bin/env python3
"""
Author : Kevin Ritchey <kevin@fortysheep.com>
Date   : 2023-06-07
Purpose: creates a config file
"""

import json
import os
import sys
import logging


# --------------------------------------------------
def test_whether_boto3_is_installed():
    """Test whether boto3 is installed"""
    try:
        import boto3
    except ImportError:
        logging.warning("ERROR: boto3 is not installed")
        return False
    
    return True


# --------------------------------------------------
def test_aws_cli_is_installed():
    """Test whether AWS CLI is installed"""
    try:
        import awscli
    except ImportError:
        logging.warning("ERROR: AWS CLI is not installed")
        return False
    
    return True

# --------------------------------------------------
def test_best_case_dir(best_case_dir):
    """Test if the Best Case directory exists"""
    if not os.path.isdir(best_case_dir):
        logging.error(f"ERROR: '{best_case_dir}' is not a directory")
        sys.exit(1)
    clients_dir = os.path.join(best_case_dir, "CLIENTS")
    if not os.path.isdir(clients_dir):
        logging.error(f"ERROR: '{clients_dir}' is not a directory")
        sys.exit(1)


# --------------------------------------------------
def create_config_file():
    config = {}

    # Prompt for Best Case installation directory
    best_case_dir = input("Where is Best Case installed? E.g. C:\\BestCase: ")
    test_best_case_dir(best_case_dir)
    config["best_case_dir"] = best_case_dir

    # Prompt for AWS S3 bucket for backups
    s3_bucket = input("What AWS S3 bucket will you use to store your backups? E.g. s3://my-bestcase-backups: ")
    config["s3_bucket"] = s3_bucket

    # Prompt for DEBUG mode
    debug_mode = input("Do you want to run the script in DEBUG mode? (Y/N): ")
    config["debug_mode"] = debug_mode.lower() == "y"

    # Save configuration to JSON file
    with open("config.json", "w") as file:
        json.dump(config, file, indent=4)

    print("Config file created successfully.")


# --------------------------------------------------
def main():
    """Make a jazz noise here"""
    # Create the config file
    create_config_file()


# --------------------------------------------------
if __name__ == '__main__':
    main()
