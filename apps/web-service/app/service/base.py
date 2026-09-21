from dataclasses import dataclass
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


@dataclass
class PageResult(Generic[T]):
    """ページング結果"""
    items: list[T]
    total: int
    page: int
    page_size: int


class BaseService:
    """ビジネスロジック基底クラス。すべての Service がこのクラスを継承し、session を共有する"""

    def __init__(self, db: AsyncSession):
        self.db = db
