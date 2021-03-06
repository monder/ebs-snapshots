import time
import os
from file_backup_config import FileBackupConfig
from s3_backup_config import S3BackupConfig
from inline_backup_config import InlineBackupConfig
import snapshot_manager
from boto import ec2
import kayvee
import logging

aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID'] if os.environ.has_key('AWS_ACCESS_KEY_ID') else None
aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY'] if os.environ.has_key('AWS_SECRET_ACCESS_KEY') else None
aws_region = os.environ['AWS_REGION']
config_path = os.environ['BACKUP_CONFIG']


def get_backup_conf(path):
    """ Gets backup config from file or S3 """
    if path.startswith("s3://"):
        return S3BackupConfig(path, aws_access_key_id, aws_secret_access_key)
    elif ":" in path:
        # config is YAML or JSON
        return InlineBackupConfig(path)
    else:
        return FileBackupConfig(path)


def create_snapshots(backup_conf):
    ec2_connection = ec2.connect_to_region(
        aws_region, aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    for volume, params in backup_conf.get().iteritems():
        logging.info(kayvee.formatLog("ebs-snapshots", "info", "about to take ebs snapshot {} - {}".format(volume, params)))
        interval = params.get('interval', 'daily')
        max_snapshots = params.get('max_snapshots', 0)
        name = params.get('name', '')
        snapshot_manager.run(
            ec2_connection, volume, interval, max_snapshots, name)


def snapshot_timer(interval=300):
    """ Gets backup conf, every x seconds checks for snapshots to create/delete,
        and performs the create/delete operations as needed """
    # Main loop gets the backup conf once.
    # Thereafter they are responsible for updating their own data
    backup_conf = get_backup_conf(config_path)
    while True:
        create_snapshots(backup_conf)
        time.sleep(interval)
