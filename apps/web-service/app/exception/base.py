"""業務例外の基底クラス

すべてのカスタム業務例外はこのクラスから派生し、上位層は ``except BusinessException`` で一括捕捉できる。
"""


class BusinessException(Exception):
    """業務例外の基底クラス

    Attributes:
        message: 外部に公開する情報。ユーザーに表示できる
        detail: 内部向けの詳細情報。開発者のログ記録と問題調査用
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
