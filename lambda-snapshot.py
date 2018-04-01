"""Snapshot every volume tagged with BACKUP_TAG. Delete snapshots after they are
DEFAULT_DAYS days old"""


import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List

import boto3


BACKUP_TAG = 'BackupDays'
DEFAULT_DAYS = '7'
DEFAULT_NAME = 'Unknown'
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
REGION = os.environ['REGION']
EC2 = boto3.resource('ec2', region_name=REGION)

logging.getLogger().setLevel(getattr(logging, LOG_LEVEL.upper()))

LOG = logging.getLogger(__name__)


def lambda_handler(*_) -> Dict[str, bool]:
    """Module entrypoint"""
    new = [j for i in get_instances() for j in create_snapshots(i)]
    LOG.info(f'Created: {len(new)} snapshots')

    deleted = [delete_snapshot(i) for i in get_old_snapshots()]
    LOG.info(f'Deleted: {len(deleted)} snapshots')

    return {'ok': True}


def get_instances() -> List[object]:
    """Get instances to back up"""
    return EC2.instances.filter(
        Filters=[dict(
            Name=f'tag:{BACKUP_TAG}',
            Values=['*'],
        )],
    )


def create_snapshots(instance: object) -> List[object]:
    """Given an instance, get snapshots of all the EBS volumes"""
    attributes = get_instance_attributes(instance)
    tags = {
        'InstanceId': instance.id,
        'InstanceName': attributes.get('Name', DEFAULT_NAME),
        BACKUP_TAG: attributes.get('Period', DEFAULT_DAYS),
    }

    return [create_snapshot(volume, tags) for volume in instance.volumes.all()]


def create_snapshot(volume: object, tags: Dict[str, str]) -> str:
    """Take a snapshot of volume"""
    mountpoints = dict(
        Mountpoints=','.join([i.get('Device') for i in volume.attachments])
    )
    tags = {**tags, **mountpoints}
    snapshot = volume.create_snapshot(Description='Lambda backup')
    snapshot.create_tags(
        Tags=[
            {'Key': str(key), 'Value': str(value)} for key, value in tags.items()
        ]
    )
    return snapshot.snapshot_id


def get_instance_attributes(instance: object) -> Dict[str, str]:
    """Get instances name from tags"""
    result = {}
    for tag in instance.tags:
        if tag['Key'] == 'Name':
            result['Name'] = tag['Value']
        elif tag['Key'] == BACKUP_TAG:
            result['Period'] = tag['Value']

    return result


def get_offset(offset: str, tzinfo) -> datetime:
    """Get a timezone aware offset from current time"""
    now = datetime.now(tzinfo)
    return now - timedelta(days=int(offset))


def delete_snapshot(snapshot: object) -> bool:
    """Delete snapshot. Return success/failure"""
    snapshot.delete()
    return True


def get_old_snapshots() -> List[object]:
    """Get a list of expired snapshots"""
    snapshots = EC2.snapshots.filter(
        Filters=[dict(
            Name=f'tag:{BACKUP_TAG}',
            Values=['*'],
        )],
    )
    result = []
    for snapshot in snapshots:
        retention = [i['Value'] for i in snapshot.tags if i['Key'] == BACKUP_TAG][0]
        if snapshot.start_time < get_offset(retention, snapshot.start_time.tzinfo):
            result.append(snapshot)

    return result
