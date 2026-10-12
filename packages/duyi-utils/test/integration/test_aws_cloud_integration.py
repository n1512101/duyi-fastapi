"""集成测试：使用真实的 AWS S3 环境进行测试。

要求：
  1. 在项目根目录提供 .env.test 文件，包含 AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION / AWS_BUCKET_NAME。
  2. 该 Bucket 需要有读写权限。
"""

import base64
import json
import os
from datetime import datetime, timezone

import pytest
from dotenv import load_dotenv

# 実際のプロジェクト構造に合わせてインポートパスを調整してください
from duyi_utils.upload.aws_cloud import AWSS3Config, AWSS3Uploader

load_dotenv(
    dotenv_path=os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", ".env.test"
    )
)


@pytest.fixture(scope="module")
def config():
    return AWSS3Config(
        access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        access_key_secret=os.environ["AWS_SECRET_ACCESS_KEY"],
        bucket_name=os.environ["AWS_BUCKET_NAME"],
        region_name=os.environ["AWS_REGION"],
        mime_types=["image/png", "image/jpeg", "application/pdf"],
    )


@pytest.fixture(scope="module")
def uploader(config):
    return AWSS3Uploader(config)


class TestGenerateUploadCredentialsIntegration:
    def test_returns_required_fields(self, uploader):
        result = uploader.generate_upload_credentials("photo.png", 1024)
        for field in ("host", "key", "content_type", "aws_fields"):
            assert field in result
            assert result[field]

        # AWS特有のフィールドが含まれているか確認
        aws_fields = result["aws_fields"]
        assert "policy" in aws_fields
        assert "x-amz-signature" in aws_fields
        assert "x-amz-credential" in aws_fields

    def test_host_matches_s3_url(self, uploader, config):
        result = uploader.generate_upload_credentials("photo.png", 1024)
        # Boto3が生成するURLには通常s3とリージョン名が含まれます
        assert config.bucket_name in result["host"]
        assert "s3" in result["host"]
        assert "amazonaws.com" in result["host"]

    def test_key_starts_with_uploads(self, uploader):
        result = uploader.generate_upload_credentials("photo.png", 1024)
        assert result["key"].startswith("uploads/")

    def test_key_ends_with_correct_suffix(self, uploader):
        result = uploader.generate_upload_credentials("photo.png", 1024)
        assert result["key"].endswith(".png")

    def test_content_type_matches_file_suffix(self, uploader):
        result = uploader.generate_upload_credentials("photo.png", 1024)
        assert result["content_type"] == "image/png"

        result = uploader.generate_upload_credentials("report.pdf", 2048)
        assert result["content_type"] == "application/pdf"

    def test_policy_can_be_decoded(self, uploader):
        result = uploader.generate_upload_credentials("photo.png", 1024)
        policy_json = base64.b64decode(result["aws_fields"]["policy"]).decode()
        policy_dict = json.loads(policy_json)

        assert "expiration" in policy_dict
        assert "conditions" in policy_dict
        conditions = policy_dict["conditions"]

        # 辞書形式とリスト形式のconditionが混ざるため、フラットにチェックします
        condition_str = json.dumps(conditions)
        assert result["key"] in condition_str
        assert "image/png" in condition_str
        assert "content-length-range" in condition_str


def _build_multipart_body(
    cred, filename, content, key_override=None, content_type_override=None
):
    """拼装 AWS S3 PostObject 的 multipart/form-data 请求体"""
    boundary = "----TestBoundary"
    body_parts = []

    fields = cred["aws_fields"].copy()

    if key_override is not None:
        fields["key"] = key_override
    if content_type_override is not None:
        fields["Content-Type"] = content_type_override

    # 1. boto3が生成したすべてのフィールドをフォームデータに追加
    for field_name, field_value in fields.items():
        body_parts.extend(
            [
                f"--{boundary}",
                f'Content-Disposition: form-data; name="{field_name}"',
                "",
                str(field_value),
            ]
        )

    # 2. AWS S3の仕様として、'file' フィールドは必ず最後に配置する必要があります
    ct = (
        content_type_override
        if content_type_override is not None
        else cred["content_type"]
    )
    body_parts.extend(
        [
            f"--{boundary}",
            f'Content-Disposition: form-data; name="file"; filename="{filename}"',
            f"Content-Type: {ct}",
            "",
            content,
            f"--{boundary}--",
            "",  # 最後の改行用
        ]
    )

    body = "\r\n".join(body_parts).encode()
    return body, boundary


def _do_upload(cred, body, boundary):
    """执行 AWS S3 PostObject 上传请求，返回响应"""
    import urllib.request

    req = urllib.request.Request(
        cred["host"],
        data=body,
        method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    return urllib.request.urlopen(req)


class TestUploadAndDelete:
    async def test_upload_delete_and_exists_flow(self, uploader):
        """完整流程测试：
        1. 生成上传凭证
        2. 上传一个测试文件到 AWS S3
        3. 检查文件存在
        4. 删除文件
        5. 确认文件不存在
        """
        cred = uploader.generate_upload_credentials("test.png", 1024)
        body, boundary = _build_multipart_body(cred, "test.png", "fake-image-content")

        response = _do_upload(cred, body, boundary)
        assert response.status == 204  # S3のPostObject成功時のデフォルトステータスは204

        assert await uploader.exists(cred["key"]) is True

        await uploader.delete(cred["key"])

        assert await uploader.exists(cred["key"]) is False

    def test_upload_with_wrong_key_rejected(self, uploader):
        """验证：获得签名后更换 Key 上传会被 AWS S3 拒绝"""
        import urllib.error

        cred = uploader.generate_upload_credentials("test.png", 1024)
        wrong_key = cred["key"].replace("uploads/", "uploads_fake/")
        body, boundary = _build_multipart_body(
            cred, "test.png", "fake-image-content", key_override=wrong_key
        )

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _do_upload(cred, body, boundary)
        assert exc_info.value.code in (400, 403)

    def test_upload_with_wrong_content_type_rejected(self, uploader):
        """验证：获得签名后更换 Content-Type 上传会被 AWS S3 拒绝"""
        import urllib.error

        cred = uploader.generate_upload_credentials("test.png", 1024)
        wrong_content_type = "image/jpeg"
        body, boundary = _build_multipart_body(
            cred,
            "test.png",
            "fake-image-content",
            content_type_override=wrong_content_type,
        )

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _do_upload(cred, body, boundary)
        assert exc_info.value.code in (400, 403)

    def test_upload_with_exceeded_file_size_rejected(self, uploader):
        """验证：上传文件大小超过签名中指定的大小会被 AWS S3 拒绝"""
        import urllib.error

        cred = uploader.generate_upload_credentials("test.png", 1024)
        large_content = "x" * 2048
        body, boundary = _build_multipart_body(cred, "test.png", large_content)

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _do_upload(cred, body, boundary)
        assert exc_info.value.code in (400, 403)
