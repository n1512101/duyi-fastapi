import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

# インポート元は実際のプロジェクト構成に合わせてください
from duyi_utils.upload.aws_cloud import AWSS3Config, AWSS3Uploader


@pytest.fixture
def config():
    return AWSS3Config(
        access_key_id="test-access-key-id",
        access_key_secret="test-access-key-secret",
        bucket_name="test-bucket",
        region_name="ap-northeast-1",
        mime_types=["image/png", "application/pdf"],
    )


@pytest.fixture
def mock_s3_client():
    with patch("boto3.client") as mock_client:
        yield mock_client.return_value


@pytest.fixture
def uploader(config, mock_s3_client):
    # 初期化時にboto3.clientが呼ばれるため、mock_s3_clientフィクスチャを経由します
    return AWSS3Uploader(config)


class TestGenerateUploadCredentials:
    def test_successful_credential_generation(self, config):
        with (
            patch("boto3.client") as mock_boto,
            patch("duyi_utils.upload.aws_cloud.uuid.uuid4") as mock_uuid,
            patch("duyi_utils.upload.dir_strategy.datetime") as mock_dir_dt,
        ):

            mock_uuid.return_value.hex = "a1b2c3d4e5f6"
            mock_dir_dt.now.return_value = datetime(2025, 6, 26, 10, 0, 0)

            # boto3の generate_presigned_post の戻り値をモック
            mock_client_instance = mock_boto.return_value
            mock_client_instance.generate_presigned_post.return_value = {
                "url": "https://test-bucket.s3.ap-northeast-1.amazonaws.com/",
                "fields": {
                    "key": "uploads/2025/06/26/a1b2c3d4e5f6.png",
                    "AWSAccessKeyId": "test-access-key-id",
                    "policy": "mock_policy",
                    "signature": "mock_signature",
                },
            }

            uploader = AWSS3Uploader(config)
            result = uploader.generate_upload_credentials("photo.png", 102400)

        # 戻り値の形式が正しいか検証
        assert result["host"] == "https://test-bucket.s3.ap-northeast-1.amazonaws.com/"
        assert result["content_type"] == "image/png"
        assert result["key"] == "uploads/2025/06/26/a1b2c3d4e5f6.png"
        assert "aws_fields" in result
        assert result["aws_fields"]["policy"] == "mock_policy"

        # boto3のメソッドが正しいパラメータ（ConditionsやExpiresIn）で呼ばれたか検証
        mock_client_instance.generate_presigned_post.assert_called_once_with(
            Bucket="test-bucket",
            Key="uploads/2025/06/26/a1b2c3d4e5f6.png",
            Fields={"Content-Type": "image/png"},
            Conditions=[
                {"Content-Type": "image/png"},
                ["content-length-range", 0, 102400],
            ],
            ExpiresIn=3600,
        )

    def test_raises_on_missing_suffix(self, config):
        with patch("boto3.client"):
            uploader = AWSS3Uploader(config)
            with pytest.raises(ValueError, match="ファイル拡張子を取得できません"):
                uploader.generate_upload_credentials("noext", 1024)

    def test_raises_on_unsupported_type(self, config):
        with patch("boto3.client"):
            uploader = AWSS3Uploader(config)
            with pytest.raises(
                ValueError, match="サポートされていないファイル形式です"
            ):
                uploader.generate_upload_credentials("file.xyz", 1024)

    def test_raises_on_not_allowed_mime_type(self, config):
        config.mime_types = ["application/pdf"]
        with patch("boto3.client"):
            uploader = AWSS3Uploader(config)
            with pytest.raises(
                ValueError, match="許可されていないアップロード形式です"
            ):
                uploader.generate_upload_credentials("photo.png", 1024)

    def test_path_filename_extracts_basename(self, config):
        with (
            patch("boto3.client") as mock_boto,
            patch("duyi_utils.upload.aws_cloud.uuid.uuid4") as mock_uuid,
            patch("duyi_utils.upload.dir_strategy.datetime") as mock_dir_dt,
        ):

            mock_uuid.return_value.hex = "a1b2c3d4e5f6"
            mock_dir_dt.now.return_value = datetime(2025, 6, 26, 10, 0, 0)

            mock_client_instance = mock_boto.return_value
            mock_client_instance.generate_presigned_post.return_value = {
                "url": "dummy",
                "fields": {},
            }

            uploader = AWSS3Uploader(config)
            result = uploader.generate_upload_credentials("/a/b/c/report.pdf", 1024)

        # パスが除去され、PDFとして認識されるか
        assert result["content_type"] == "application/pdf"
        assert result["key"].endswith(".pdf")


class TestDelete:
    async def test_delete_calls_bucket_delete_object(self, uploader, mock_s3_client):
        await uploader.delete("uploads/2025/06/26/test.png")

        # boto3のdelete_objectが正しい引数で呼ばれたか検証
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="uploads/2025/06/26/test.png"
        )


class TestExists:
    async def test_exists_true(self, uploader, mock_s3_client):
        # 例外が発生しなければ存在するとみなす
        mock_s3_client.head_object.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200}
        }

        result = await uploader.exists("uploads/2025/06/26/test.png")
        assert result is True
        mock_s3_client.head_object.assert_called_once_with(
            Bucket="test-bucket", Key="uploads/2025/06/26/test.png"
        )

    async def test_exists_false_on_404(self, uploader, mock_s3_client):
        # 404エラーの場合はFalseを返す仕様のテスト
        error_response = {"Error": {"Code": "404", "Message": "Not Found"}}
        mock_s3_client.head_object.side_effect = ClientError(
            error_response, "HeadObject"
        )

        result = await uploader.exists("uploads/2025/06/26/test.png")
        assert result is False

    async def test_exists_raises_other_errors(self, uploader, mock_s3_client):
        # 404以外のエラー（権限エラーの403など）はそのまま例外として投げる仕様のテスト
        error_response = {"Error": {"Code": "403", "Message": "Forbidden"}}
        mock_s3_client.head_object.side_effect = ClientError(
            error_response, "HeadObject"
        )

        with pytest.raises(ClientError):
            await uploader.exists("uploads/2025/06/26/test.png")
