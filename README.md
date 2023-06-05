## Automated Backup Program for Windows using Python 3.11 and AWS S3

This GitHub repository contains an automated backup program written in Python 3.11, specifically designed for Windows computers. The program utilizes the 7zip utility for compressing a specified directory and interacts with AWS S3 using the boto3 library to store the backup securely in the cloud.

### Features
- Automated backup: The program can be scheduled to run automatically using Task Scheduler, ensuring regular and consistent backups.
- Directory backup: It accepts a single directory as input for backup, allowing users to choose the specific data they want to safeguard.
- Compression with 7zip: The program compresses the specified directory using 7zip, optimizing storage space while maintaining data integrity.
- AWS S3 integration: It securely authenticates and connects to AWS S3 using appropriate AWS credentials, allowing for seamless backup to the cloud.
- Backup retention policy: The program includes functionality to prune backups stored in AWS S3 that are older than 7 days, ensuring efficient management of storage resources.
- Error handling and logging: It handles any errors encountered during the backup process, providing meaningful error messages and logging relevant information such as start time, completion time, and encountered errors.

### Usage
1. Ensure Python 3.11, 7zip, and the boto3 library are installed on your Windows computer.
2. Clone or download the repository to your local machine.
3. Configure the AWS credentials and backup directory settings in the program.
4. Schedule the program to run automatically using Task Scheduler, specifying the desired backup frequency.
5. The program will compress the specified directory using 7zip and securely upload the backup file to the designated AWS S3 bucket.
6. Backups older than 7 days will be automatically pruned from the S3 bucket, adhering to the retention policy.

### Contributions
Contributions to this project are welcome! If you have any ideas, improvements, or bug fixes, feel free to open an issue or submit a pull request.

### License
This program is licensed under the [MIT License](https://opensource.org/licenses/MIT).

### Disclaimer
Please note that the program is provided as-is and users are responsible for testing and ensuring its suitability for their specific use cases. The program may undergo further updates and enhancements based on community feedback and requirements.

**Note:** Please consult the documentation within the repository for detailed instructions on configuring and using the automated backup program.
