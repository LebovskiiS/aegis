"""Ship the audit log to long-term storage (object store or a local dir).

Configured via the `audit.sink` section of aegis.yaml (mapped to env). Run on a
schedule (cron) or manually:  aegis audit-ship --config aegis.yaml

  type: none   -> do nothing
  type: local  -> copy to <bucket>/<prefix><ts>-audit.log   (works out of the box)
  type: s3     -> upload to s3://<bucket>/...   (pip install 'aegis-docs[s3]')
  type: gcs    -> upload to gs://<bucket>/...   (pip install 'aegis-docs[gcs]')
"""
from __future__ import annotations

import os
import shutil
import time
from pathlib import Path


def ship() -> str:
    sink = os.getenv("AEGIS_AUDIT_SINK", "none")
    if sink == "none":
        return "audit sink = none (nothing to do)"

    log = Path(os.getenv("AEGIS_AUDIT_LOG", "audit.log"))
    if not log.exists():
        return "no audit log to ship"

    bucket = os.getenv("AEGIS_AUDIT_BUCKET", "")
    prefix = os.getenv("AEGIS_AUDIT_PREFIX", "aegis/audit/")
    key = f"{prefix}{int(time.time())}-{log.name}"

    if sink == "local":
        dest = Path(bucket or "audit-archive") / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(log, dest)
        return f"copied -> {dest}"

    if sink == "s3":
        import boto3  # optional: pip install 'aegis-docs[s3]'

        boto3.client("s3").upload_file(str(log), bucket, key)
        return f"uploaded -> s3://{bucket}/{key}"

    if sink == "gcs":
        from google.cloud import storage  # optional: pip install 'aegis-docs[gcs]'

        storage.Client().bucket(bucket).blob(key).upload_from_filename(str(log))
        return f"uploaded -> gs://{bucket}/{key}"

    return f"unknown audit sink: {sink}"
