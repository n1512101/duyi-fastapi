from sqlalchemy import delete, exc as sa_exc, func, insert, select
from sqlalchemy.orm import selectinload

from app.model.association import product_category
from app.model.category import Category
from app.model.product import Product
from app.schema.product import (
    ProductBrief,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.service.base import BaseService, PageResult
from app.exception.database import DatabaseException


class ProductService(BaseService):
    async def create_product(self, data: ProductCreate) -> ProductResponse:
        """商品を作成し、同時にカテゴリとの関連を構築する"""
        product = Product(
            name=data.name,
            description=data.description,
            brand=data.brand,
        )
        self.db.add(product)
        await self.db.flush()

        if data.category_ids:
            try:
                await self.db.execute(
                    insert(product_category),
                    [
                        {"product_id": product.id, "category_id": cid}
                        for cid in data.category_ids
                    ],
                )
            except sa_exc.IntegrityError as e:
                raise DatabaseException(
                    message="関連するカテゴリが存在しません",
                    detail=str(e),
                    original_exception=e,
                ) from e

        result = await self.get_product(product.id)
        assert result is not None
        return result

    async def get_product(self, product_id: int) -> ProductResponse | None:
        """ID で商品詳細を取得する。関連するカテゴリリストと SKU リストを含む"""
        stmt = (
            select(Product)
            .options(selectinload(Product.categories), selectinload(Product.skus))
            .where(Product.id == product_id)
        )
        result = await self.db.execute(stmt)
        product = result.unique().scalar_one_or_none()
        if product is None:
            return None
        return ProductResponse.model_validate(product)

    async def list_products(
        self,
        *,
        keyword: str | None = None,
        category_id: int | None = None,
        brand: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PageResult[ProductBrief]:
        """商品リストをページングで検索する。キーワード・カテゴリ・ブランドによる絞り込みに対応"""
        query = select(Product)

        if category_id is not None:
            query = query.join(Product.categories).where(Category.id == category_id)

        if keyword:
            query = query.where(
                Product.name.ilike(f"%{keyword}%")
                | Product.description.ilike(f"%{keyword}%")
            )

        if brand:
            query = query.where(Product.brand.ilike(f"%{brand}%"))

        total = await self.db.scalar(
            select(func.count()).select_from(query.subquery())
        )

        offset = (page - 1) * page_size
        result = await self.db.execute(
            query.offset(offset).limit(page_size).order_by(Product.id.desc())
        )
        items = [
            ProductBrief.model_validate(p) for p in result.unique().scalars().all()
        ]

        return PageResult(items=items, total=total or 0, page=page, page_size=page_size)

    async def update_product(
        self, product_id: int, data: ProductUpdate
    ) -> ProductResponse | None:
        """商品情報を更新する。渡されたフィールドのみ更新"""
        product = await self._get_product_orm(product_id)
        if product is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        category_ids = update_data.pop("category_ids", None)

        for key, value in update_data.items():
            setattr(product, key, value)

        if category_ids is not None:
            await self.db.execute(
                delete(product_category).where(
                    product_category.c.product_id == product_id
                )
            )
            if category_ids:
                try:
                    await self.db.execute(
                        insert(product_category),
                        [
                            {"product_id": product_id, "category_id": cid}
                            for cid in category_ids
                        ],
                    )
                except sa_exc.IntegrityError as e:
                    raise DatabaseException(
                        message="関連するカテゴリが存在しません",
                        detail=str(e),
                        original_exception=e,
                    ) from e

        await self.db.flush()
        # 再読み込みして、返却する DTO に最新の関連データが含まれることを保証する
        return await self.get_product(product_id)

    async def delete_product(self, product_id: int) -> bool:
        """商品を削除する。関連する SKU はカスケード削除される"""
        product = await self._get_product_orm(product_id)
        if product is None:
            return False
        await self.db.delete(product)
        await self.db.flush()
        return True

    async def _get_product_orm(self, product_id: int) -> Product | None:
        """内部メソッド: 更新/削除用に ORM オブジェクトを取得する"""
        stmt = (
            select(Product)
            .options(selectinload(Product.categories), selectinload(Product.skus))
            .where(Product.id == product_id)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()
