from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.model.category import Category
from app.schema.category import (
    CategoryCreate,
    CategoryDetailResponse,
    CategoryResponse,
    CategoryUpdate,
)
from app.service.base import BaseService, PageResult


class CategoryService(BaseService):
    async def create_category(self, data: CategoryCreate) -> CategoryResponse:
        """カテゴリを作成する"""
        category = Category(name=data.name, description=data.description)
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return CategoryResponse.model_validate(category)

    async def get_category(
        self, category_id: int
    ) -> CategoryDetailResponse | None:
        """ID でカテゴリ詳細を取得する。関連する商品リストを含む"""
        stmt = (
            select(Category)
            .options(selectinload(Category.products))
            .where(Category.id == category_id)
        )
        result = await self.db.execute(stmt)
        category = result.unique().scalar_one_or_none()
        if category is None:
            return None
        return CategoryDetailResponse.model_validate(category)

    async def list_categories(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> PageResult[CategoryResponse]:
        """カテゴリリストをページングで取得する"""
        total = await self.db.scalar(select(func.count(Category.id)))

        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(Category)
            .offset(offset)
            .limit(page_size)
            .order_by(Category.id.asc())
        )
        items = [
            CategoryResponse.model_validate(c) for c in result.scalars().all()
        ]

        return PageResult(items=items, total=total or 0, page=page, page_size=page_size)

    async def update_category(
        self, category_id: int, data: CategoryUpdate
    ) -> CategoryResponse | None:
        """カテゴリ情報を更新する。渡されたフィールドのみ更新"""
        category = await self._get_category_orm(category_id)
        if category is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(category, key, value)

        await self.db.flush()
        await self.db.refresh(category)
        return CategoryResponse.model_validate(category)

    async def delete_category(self, category_id: int) -> bool:
        """カテゴリを削除する"""
        category = await self._get_category_orm(category_id)
        if category is None:
            return False
        await self.db.delete(category)
        await self.db.flush()
        return True

    async def _get_category_orm(self, category_id: int) -> Category | None:
        """内部メソッド: 更新/削除用に ORM オブジェクトを取得する"""
        stmt = select(Category).where(Category.id == category_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
