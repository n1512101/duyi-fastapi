import asyncio
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

from duyi_utils.shared.file_util import get_suffix
from duyi_utils.shared.mime import get_mime_type
from duyi_utils.upload.dir_strategy import date_uuid_strategy


@dataclass
class AWSS3Config:
    """AWS S3 アップロード設定"""

    access_key_id: str
    access_key_secret: str
    bucket_name: str
    region_name: (
        str  # AWSではendpointの代わりにregion_name（例: ap-northeast-1）を使用します
    )
    dir_strategy: Callable[[], str] = field(default=date_uuid_strategy)
    expire_seconds: int = 3600
    mime_types: list[str] | None = None


class AWSS3Uploader:
    """AWS S3 アップローダー。アップロード憑証の生成、削除、存在確認機能を提供します。"""

    def __init__(self, config: AWSS3Config):
        self._config = config

        # boto3のS3クライアントを初期化（AWSの推奨するSigV4署名を指定）
        self._s3_client = boto3.client(
            "s3",
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.access_key_secret,
            region_name=config.region_name,
            endpoint_url=f"https://s3.{config.region_name}.amazonaws.com",
            config=Config(signature_version="s3v4"),
        )

    def generate_upload_credentials(self, filename: str, file_size: int) -> dict:
        """
        AWS S3のPresigned POST（署名付きURL）用のアップロード憑証を生成します。
        """
        basename = os.path.basename(filename)
        suffix = get_suffix(basename)
        if suffix is None:
            raise ValueError(f"ファイル拡張子を取得できません: {basename}")

        content_type = get_mime_type(suffix)
        if content_type is None:
            raise ValueError(f"サポートされていないファイル形式です: .{suffix}")

        if self._config.mime_types and content_type not in self._config.mime_types:
            raise ValueError(f"許可されていないアップロード形式です: {content_type}")

        dir_ = self._config.dir_strategy()
        key = f"{dir_}{uuid.uuid4().hex}.{suffix}"

        # boto3の機能を使ってポリシー生成と署名を自動化
        conditions = [
            {"Content-Type": content_type},
            ["content-length-range", 0, file_size],
        ]

        # generate_presigned_post はURLと、POSTに必要な全フィールド（policy, signature等）の辞書を返します
        presigned_data = self._s3_client.generate_presigned_post(
            Bucket=self._config.bucket_name,
            Key=key,
            Fields={"Content-Type": content_type},
            Conditions=conditions,
            ExpiresIn=self._config.expire_seconds,
        )

        return {
            "host": presigned_data["url"],  # POST先のエンドポイントURL
            "key": key,
            "content_type": content_type,
            # AWSの場合、policy, x-amz-signature, x-amz-credentialなど複数フィールドが返るため、
            # まとめて返却し、フロントエンドでループしてFormDataに追加させます
            "aws_fields": presigned_data["fields"],
        }

    async def delete(self, object_key: str) -> None:
        """
        S3上の指定されたkeyのファイルを削除します。
        """

        def _delete():
            self._s3_client.delete_object(
                Bucket=self._config.bucket_name, Key=object_key
            )

        # boto3は同期ライブラリなので、イベントループをブロックしないよう別スレッドで実行
        await asyncio.to_thread(_delete)

    async def exists(self, object_key: str) -> bool:
        """
        S3上の指定されたkeyのファイルが存在するか判定します。
        """

        def _exists():
            try:
                # メタデータのみを取得して存在確認
                self._s3_client.head_object(
                    Bucket=self._config.bucket_name, Key=object_key
                )
                return True
            except ClientError as e:
                # 404 Not Found の場合は存在しないとみなす
                if e.response["Error"]["Code"] == "404":
                    return False
                # それ以外のエラー（権限不足など）は例外を投げる
                raise e

        return await asyncio.to_thread(_exists)
