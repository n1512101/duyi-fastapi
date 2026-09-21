"""業務例外の基底クラス

すべてのカスタム業務例外はこのクラスから派生し、上位レイヤーでは ``except BusinessException`` で一括して捕捉できます。
"""


class BusinessException(Exception):
    """業務例外の基底クラス

    Attributes:
        message: 外部に公開する情報。ユーザーに表示可能
        detail: 内部向けの詳細情報。開発者のログ記録や問題調査に使用
        original_exception: 元の例外インスタンス。根本原因の追跡に役立つ
    """

    def __init__(
        self,
        message: str,
        *,
        detail: str = "",
        original_exception: Exception | None = None,
    ):
        self.message = message
        self.detail = detail
        self.original_exception = original_exception
        super().__init__(message)
