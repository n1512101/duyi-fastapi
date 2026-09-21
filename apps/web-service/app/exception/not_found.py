"""リソースが存在しない例外"""

from app.exception.base import BusinessException


class NotFoundException(BusinessException):
    """リソースが存在しない業務例外"""

    pass
