from __future__ import annotations
import os, time
from typing import Optional
from backend.utils.env_setup import get_logger

try:
    import boto3  # type: ignore
    HAS_BOTO3 = True
except Exception:
    HAS_BOTO3 = False

class BlobStore:
    def save_text(self, namespace: str, base_id: str, text: str) -> str:
        raise NotImplementedError

class LocalBlobStore(BlobStore):
    def __init__(self, persist_dir: str) -> None:
        self.logger = get_logger("LocalBlobStore")
        self.base = os.path.join(persist_dir, "blobs")
        os.makedirs(self.base, exist_ok=True)

    def save_text(self, namespace: str, base_id: str, text: str) -> str:
        ns = self._sanitize(namespace)
        safe = self._sanitize(base_id) + ".txt"
        p = os.path.join(self.base, ns)
        os.makedirs(p, exist_ok=True)
        fp = os.path.join(p, safe)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(text or "")
        return fp

    def _sanitize(self, s: str) -> str:
        import re
        return re.sub(r"[^a-zA-Z0-9._-]+", "-", s)[:128] or "blob"

class S3BlobStore(BlobStore):
    def __init__(self, bucket: str, prefix: str = "") -> None:
        if not HAS_BOTO3:
            raise RuntimeError("boto3 is required for S3BlobStore")
        self.logger = get_logger("S3BlobStore")
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.s3 = boto3.client("s3")

    def save_text(self, namespace: str, base_id: str, text: str) -> str:
        key = "/".join(x for x in [self.prefix or None, namespace, base_id + ".txt"] if x)
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=(text or "").encode("utf-8"), ContentType="text/plain")
        # return a presigned URL valid for 7 days
        try:
            url = self.s3.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=7 * 24 * 3600,
            )
            return url
        except Exception:
            return f"s3://{self.bucket}/{key}"
