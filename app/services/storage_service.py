"""
Objekt-Speicher für hochgeladene Dokumente/Bilder via Cloudflare R2
(S3-kompatibel). Ersetzt lokale Disk-Ablage, die auf Render bei jedem
Redeploy/Neustart verloren geht.

Erwartet folgende Env-Variablen (siehe .env.example):
  R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME, R2_ENDPOINT_URL

R2_ENDPOINT_URL muss zum Hoheitsgebiet des Buckets passen (z.B. auf ein
EU-only-Bucket bezogen die eu.r2.cloudflarestorage.com-Domain, nicht die
account-weite Standard-Domain) – Cloudflare zeigt den richtigen Wert beim
Erstellen des API-Tokens an.

Ist R2 nicht konfiguriert (z.B. lokale Entwicklung/Tests ohne eigenen
Bucket), wird automatisch auf lokale Disk-Ablage unter uploads/
zurückgefallen – identisches Verhalten zu vorher, nur kein Production-Fallback
(auf Render sind die R2-Variablen Pflicht, siehe README).
"""
import os
from pathlib import Path

import boto3
from botocore.client import Config

_R2_ACCOUNT_ID  = os.getenv("R2_ACCOUNT_ID")
_R2_ACCESS_KEY  = os.getenv("R2_ACCESS_KEY_ID")
_R2_SECRET_KEY  = os.getenv("R2_SECRET_ACCESS_KEY")
_R2_ENDPOINT    = os.getenv("R2_ENDPOINT_URL") or (
    f"https://{_R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if _R2_ACCOUNT_ID else None
)
BUCKET_NAME     = os.getenv("R2_BUCKET_NAME", "onboardguide-documents")

R2_CONFIGURED = bool(_R2_ACCOUNT_ID and _R2_ACCESS_KEY and _R2_SECRET_KEY)

_LOCAL_DIR = Path("uploads")
_LOCAL_DIR.mkdir(exist_ok=True)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = boto3.client(
            "s3",
            endpoint_url=_R2_ENDPOINT,
            aws_access_key_id=_R2_ACCESS_KEY,
            aws_secret_access_key=_R2_SECRET_KEY,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
    return _client


def _local_path(key: str) -> Path:
    path = _LOCAL_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def upload_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    if not R2_CONFIGURED:
        _local_path(key).write_bytes(data)
        return
    _get_client().put_object(
        Bucket=BUCKET_NAME, Key=key, Body=data, ContentType=content_type
    )


def download_bytes(key: str) -> bytes:
    if not R2_CONFIGURED:
        return _local_path(key).read_bytes()
    obj = _get_client().get_object(Bucket=BUCKET_NAME, Key=key)
    return obj["Body"].read()


def delete_object(key: str) -> None:
    if not R2_CONFIGURED:
        _local_path(key).unlink(missing_ok=True)
        return
    _get_client().delete_object(Bucket=BUCKET_NAME, Key=key)
