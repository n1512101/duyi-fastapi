from pydantic_settings import BaseSettings


class _BaseSettingsWithEnv(BaseSettings):
    # 設定の読み込み方法
    model_config = {"env_file": "apps/.env", "extra": "ignore"}  # env ファイルの場所


# 共通設定
class _CommonSettings(_BaseSettingsWithEnv):
    environment: str = "development"


# Web サービス設定
class _WebSettings(_BaseSettingsWithEnv):
    app_name: str = "Web Service API"  # 実際には WEB_APP_NAME を読み取る

    # 設定の読み込み方法
    model_config = {"env_prefix": "WEB_"}


# データベース設定
class _DBSettings(_BaseSettingsWithEnv):
    host: str = ""
    port: str = ""
    name: str = ""
    user: str = ""
    password: str = ""

    model_config = {"env_prefix": "DB_"}


common_settings = _CommonSettings()
web_settings = _WebSettings()
db_settings = _DBSettings()
