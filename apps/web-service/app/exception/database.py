from app.exception.base import BusinessException


class DatabaseException(BusinessException):
    """データベース操作の例外（一意制約違反、外部キー制約違反など）"""
    pass
