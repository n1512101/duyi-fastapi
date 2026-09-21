from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# プロジェクト設定からデータベース接続情報を読み取る
from app.core.config import db_settings

# モデルをインポート（__init__.py 経由で全モデルを Base.metadata に登録する）
from app.model.base import Base

# Alembic 設定オブジェクト。alembic.ini の読み取りに使用
config = context.config

# Python ログを設定（alembic.ini の [loggers] 設定を読み取る）
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# alembic.ini の sqlalchemy.url をプロジェクト設定で上書きする
# 同期ドライバ postgresql:// を使用（+asyncpg は不要）
config.set_main_option(
    "sqlalchemy.url",
    f"postgresql://{db_settings.user}:{db_settings.password}@{db_settings.host}:{db_settings.port}/{db_settings.name}",
)

# マイグレーションの自動作成に備え、Alembic にモデルのメタデータを伝える
target_metadata = Base.metadata

# その他の設定項目は config.get_main_option() で取得できる


def run_migrations_offline() -> None:
    """オフラインモードでマイグレーションを実行（データベースに接続せず SQL スクリプトのみ生成）"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """オンラインモードでマイグレーションを実行（データベースに直接接続して実行）"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
