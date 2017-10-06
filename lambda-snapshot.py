#!/usr/bin/env python3
"""Designed for use in AWS Lambda.
Snapshot every volume tagged with CREATE_TAG. Delete generated snapshots
after they are SNAPSHOT_PERIOD + 1 days old."""


import os
from datetime import datetime, timedelta
import boto3
import botocore


SNAPSHOT_PERIOD = 7 # Days
CREATE_TAG = {'AutoSnapshot': 'true'}
DELETE_TAG = {'AutoDelete': 'true'}
RETENTION_TAG = {'AutoDeleteDays': SNAPSHOT_PERIOD}
SNAPSHOT_DESCRIPTION = 'Automatic daily backup'
REGION = os.environ.get('AWS_REGION') or 'us-east-1'


def tags_to_filter(tags):
    """Convert a tags dict to AWS filter format"""
    tag_filter = []
    for key, value in tags.items():
        tag_filter.append(
            {
                'Name': 'tag:' + key,
                'Values': [value]
            }
        )
    return tag_filter


def take_snapshot(volume, tags):
    """Take a snapshot of volume and apply tags. Return snapshot id"""
    snapshot = volume.create_snapshot(Description=SNAPSHOT_DESCRIPTION)
    snapshot.create_tags(
        Tags=[
            {'Key': str(key), 'Value': str(value)} for key, value in tags.items()
        ]
    )
    return (snapshot.snapshot_id, volume.id)


def get_instances(ec2):
    """Get a list of instances to snapshot volumes from"""
    tag_filter = tags_to_filter(CREATE_TAG)
    return ec2.instances.filter(Filters=tag_filter)


def get_instance_name(instance):
    """Given an instance, get the tag Value for Key 'Name'"""
    for tag in instance.tags:
        if tag.get('Key') == 'Name':
            return tag.get('Value')


def take_snapshots(ec2):
    """Create snapshots of the tagged instances"""
    snaps_created = 0
    tagged_instances = get_instances(ec2)
    for instance in tagged_instances:
        for volume in instance.volumes.all():
            result = take_snapshot(
                volume,
                {
                    **DELETE_TAG,
                    **RETENTION_TAG,
                    'InstanceId': instance.id,
                    'InstanceName': get_instance_name(instance) or 'Unknown',
                    'MountPoints': ', '.join([i.get('Device') for i in volume.attachments])
                }
            )
            print('Created snashot %s of volume %s' % result)
            snaps_created += 1
    return snaps_created


def get_timezone_aware_offset(offset, tzinfo):
    """Get a timezone aware offset from current time"""
    now = datetime.now(tzinfo)
    return now - timedelta(days=offset+1)


def get_snapshot_retention(tags):
    """Iterate through tags and return retention period"""
    for tag in tags:
        if tag.get('Key') == 'AutoDeleteDays':
            return tag.get('Value')


def delete_snapshots(ec2):
    """Clean up snapshots older than current - SNAPSHOT_PERIOD"""
    snaps_deleted = 0
    tag_filter = tags_to_filter(DELETE_TAG)

    snapshots = ec2.snapshots.filter(Filters=tag_filter)

    for snapshot in snapshots:
        try:
            retention = int(get_snapshot_retention(snapshot.tags))
        except ValueError:
            print('Invalid retention specified on %s, skipped' % snapshot.id)
            continue
        if snapshot.start_time < get_timezone_aware_offset(retention, snapshot.start_time.tzinfo):
            print('Deleting snapshot: %s' % snapshot.id)
            try:
                snapshot.delete()
            except botocore.exceptions.ClientError as e:
                print('Failed to delete %s: %s' % (snapshot.id, e.response))
                continue
            snaps_deleted += 1
    return snaps_deleted


def lambda_handler(*_):
    """Main function"""
    ec2 = boto3.resource('ec2', region_name=REGION)

    snaps_created = take_snapshots(ec2)
    snaps_deleted = delete_snapshots(ec2)

    return {'SnapshotsCreated': snaps_created, 'SnapshotsDeleted': snaps_deleted}
