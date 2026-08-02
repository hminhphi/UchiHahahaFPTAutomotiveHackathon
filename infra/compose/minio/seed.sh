#!/bin/sh
set -eu

mc alias set local http://minio:9000 "$FLEETIQ_OBJECT_STORAGE_ACCESS_KEY" "$FLEETIQ_OBJECT_STORAGE_SECRET_KEY"
mc mb --ignore-existing "local/$FLEETIQ_OBJECT_STORAGE_BUCKET"

# Keep object keys portable: trips/<trip-id>/kitti/... maps directly to the organizer layout.
mc mirror --overwrite /seed/Practice_Dataset/Practice_Dataset "local/$FLEETIQ_OBJECT_STORAGE_BUCKET/trips"
