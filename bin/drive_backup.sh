#!/bin/bash
set -e

. $GOOGLE_DRIVE_BACKUP_HOME/3rdparty/bin/activate
python $GOOGLE_DRIVE_BACKUP_HOME/scripts/drive_backup.py --config $GOOGLE_DRIVE_BACKUP_HOME/etc/config.json $*

