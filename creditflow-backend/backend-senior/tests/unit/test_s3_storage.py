"""DOC 5 §9, Roadmap Этап 5 п.13: S3/MinIO storage wiring.

Exercises the real `storages.backends.s3boto3.S3Boto3Storage` class against
moto's in-process S3 mock — no MinIO/Docker required (Docker Hub may be
unreachable, see RUNNING.md), while still proving the actual upload +
presigned-URL code path works, not just that settings parse.
"""
import boto3
import pytest
from moto import mock_aws

BUCKET = "creditflow-test-bucket"


@pytest.fixture
def s3_storage(settings):
    """A real S3Boto3Storage instance backed by a moto-mocked bucket."""
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)

        settings.AWS_ACCESS_KEY_ID = "testing"
        settings.AWS_SECRET_ACCESS_KEY = "testing"
        settings.AWS_STORAGE_BUCKET_NAME = BUCKET
        settings.AWS_S3_REGION_NAME = "us-east-1"
        settings.AWS_S3_ENDPOINT_URL = None
        settings.AWS_QUERYSTRING_AUTH = True
        settings.AWS_QUERYSTRING_EXPIRE = 3600
        settings.AWS_DEFAULT_ACL = None

        from storages.backends.s3boto3 import S3Boto3Storage

        yield S3Boto3Storage()


def test_uploaded_file_is_stored_in_the_bucket(s3_storage):
    from django.core.files.base import ContentFile

    name = s3_storage.save("avatars/1.jpg", ContentFile(b"fake-jpeg-bytes"))

    client = boto3.client("s3", region_name="us-east-1")
    obj = client.get_object(Bucket=BUCKET, Key=name)
    assert obj["Body"].read() == b"fake-jpeg-bytes"


def test_url_is_presigned_with_a_ttl_not_a_public_link(s3_storage):
    from django.core.files.base import ContentFile

    name = s3_storage.save("documents/1.pdf", ContentFile(b"fake-pdf-bytes"))

    url = s3_storage.url(name)

    assert "Signature" in url or "X-Amz-Signature" in url
    assert "Expires" in url or "X-Amz-Expires" in url


def test_url_is_not_a_static_public_link(s3_storage):
    """Each call must mint a fresh signature/expiry — proves the URL is
    generated per-request (real presigning), not a cached public object URL."""
    from django.core.files.base import ContentFile

    name = s3_storage.save("documents/2.pdf", ContentFile(b"secret-bytes"))

    url_1 = s3_storage.url(name)
    url_2 = s3_storage.url(name, expire=7200)

    assert url_1 != url_2
