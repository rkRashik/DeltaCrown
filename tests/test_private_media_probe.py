"""Offline regressions for read-only Supabase origin recovery canary."""
import io
import unittest
from unittest.mock import MagicMock
from botocore.exceptions import ClientError

from scripts.private_media_probe import BUCKET, inspect_private_origin, private_s3_settings, verify_unsigned_denial


class PrivateMediaProbeTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "MEDIA_PRIVATE_BUCKET": BUCKET,
            "MEDIA_PRIVATE_ENDPOINT_URL": "https://project.storage.supabase.co/storage/v1/s3",
            "MEDIA_PRIVATE_REGION": "ap-south-1",
            "MEDIA_PRIVATE_ACCESS_KEY_ID": "synthetic-key",
            "MEDIA_PRIVATE_SECRET_ACCESS_KEY": "synthetic-secret",
        }

    def client(self, count):
        fake = MagicMock()
        fake.get_paginator.return_value.paginate.return_value = [
            {"Contents": [{"Key": f"private/{i:03d}"} for i in range(count)]}
        ]
        fake.head_object.return_value = {"ContentLength": 10}
        fake.get_object.side_effect = lambda **kwargs: {"Body": io.BytesIO(b"x")}
        return fake

    def test_valid_private_origin(self):
        self.assertEqual(private_s3_settings(self.config)["bucket"], BUCKET)

    def test_wrong_or_incomplete_origin_fails_closed(self):
        for key, value in (
            ("MEDIA_PRIVATE_REGION", "auto"),
            ("MEDIA_PRIVATE_BUCKET", "public-art"),
            ("MEDIA_PRIVATE_ACCESS_KEY_ID", ""),
            ("MEDIA_PRIVATE_ENDPOINT_URL", "http://localhost/storage/v1/s3"),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                private_s3_settings({**self.config, key: value})

    def test_verifies_all_125_heads_and_five_signed_reads_without_mutation(self):
        client = self.client(125)
        self.assertEqual(inspect_private_origin(client, BUCKET, expected_bytes=1250), (125, 5, 0))
        self.assertEqual(client.head_object.call_count, 125)
        self.assertEqual(client.get_object.call_count, 5)
        for operation in ("put_object", "copy_object", "delete_object"):
            getattr(client, operation).assert_not_called()

    def test_missing_origin_objects_aborts_without_reads(self):
        client = self.client(124)
        with self.assertRaises(ValueError):
            inspect_private_origin(client, BUCKET, expected_bytes=1250)
        client.head_object.assert_not_called()
        client.get_object.assert_not_called()

    def test_empty_origin_object_aborts_without_reads(self):
        client = self.client(125)
        client.head_object.return_value = {"ContentLength": 0}
        with self.assertRaises(ValueError):
            inspect_private_origin(client, BUCKET)
        client.get_object.assert_not_called()

    def test_total_byte_mismatch_aborts_before_signed_reads(self):
        client = self.client(125)
        with self.assertRaises(ValueError):
            inspect_private_origin(client, BUCKET)
        self.assertEqual(client.head_object.call_count, 125)
        client.get_object.assert_not_called()

    def test_unsigned_head_get_denied_for_all_samples(self):
        client = self.client(125)
        denied = MagicMock()
        def deny(**kwargs):
            raise ClientError(
                {"ResponseMetadata": {"HTTPStatusCode": 403},
                 "Error": {"Code": "AccessDenied", "Message": "Denied"}},
                "GetObject",
            )
        denied.head_object.side_effect = deny
        denied.get_object.side_effect = deny
        self.assertEqual(
            inspect_private_origin(client, BUCKET, expected_bytes=1250,
                                   unsigned_client=denied), (125, 5, 10),
        )
        self.assertEqual(denied.head_object.call_count, 5)
        self.assertEqual(denied.get_object.call_count, 5)
        for operation in ("put_object", "copy_object", "delete_object"):
            getattr(denied, operation).assert_not_called()

    def test_any_unsigned_success_aborts_and_closes_body(self):
        denied = MagicMock()
        body = io.BytesIO(b"private")
        denied.head_object.side_effect = ClientError(
            {"ResponseMetadata": {"HTTPStatusCode": 403},
             "Error": {"Code": "AccessDenied", "Message": "Denied"}},
            "HeadObject",
        )
        denied.get_object.return_value = {"Body": body}
        with self.assertRaises(ValueError):
            verify_unsigned_denial(denied, BUCKET, ["synthetic/file"])
        self.assertTrue(body.closed)

    def test_unsigned_404_does_not_falsely_prove_denial(self):
        denied = MagicMock()
        denied.head_object.side_effect = ClientError(
            {"ResponseMetadata": {"HTTPStatusCode": 404},
             "Error": {"Code": "NoSuchKey", "Message": "Missing"}},
            "HeadObject",
        )
        with self.assertRaises(ValueError):
            verify_unsigned_denial(denied, BUCKET, ["synthetic/file"])
        denied.get_object.assert_not_called()

    def test_duplicate_listing_aborts_without_reads(self):
        client = self.client(125)
        client.get_paginator.return_value.paginate.return_value[0]["Contents"][-1]["Key"] = "private/000"
        with self.assertRaises(ValueError):
            inspect_private_origin(client, BUCKET)
        client.head_object.assert_not_called()
        client.get_object.assert_not_called()


if __name__ == "__main__":
    unittest.main()
