from sqlalchemy import exc as sa_exc, select

from app.model.product import Product
from app.model.sku import Sku
from app.schema.sku import SkuCreate, SkuResponse, SkuUpdate
from app.service.base import BaseService
from app.exception.database import DatabaseException


class SkuService(BaseService):
    async def create_sku(self, product_id: int, data: SkuCreate) -> SkuResponse | None:
        """指定された商品に SKU を作成する"""
        product = await self.db.get(Product, product_id)
        if product is None:
            return None

        sku = Sku(
            product_id=product_id,
            sku_code=data.sku_code,
            price=data.price,
            stock=data.stock,
            attrs=data.attrs,
            image_url=data.image_url,
        )
        self.db.add(sku)
        try:
            await self.db.flush()
        except sa_exc.IntegrityError as e:
            raise DatabaseException(
                message="SKUコードが重複しています",
                detail=str(e),
                original_exception=e,
            ) from e
        await self.db.refresh(sku)
        return SkuResponse.model_validate(sku)

    async def get_sku(self, sku_id: int) -> SkuResponse | None:
        """ID で SKU 詳細を取得する"""
        stmt = select(Sku).where(Sku.id == sku_id)
        result = await self.db.execute(stmt)
        sku = result.scalar_one_or_none()
        if sku is None:
            return None
        return SkuResponse.model_validate(sku)

    async def list_skus(self, product_id: int) -> list[SkuResponse]:
        """指定された商品に属するすべての SKU を取得する"""
        stmt = select(Sku).where(Sku.product_id == product_id)
        result = await self.db.execute(stmt)
        return [SkuResponse.model_validate(s) for s in result.scalars().all()]

    async def update_sku(self, sku_id: int, data: SkuUpdate) -> SkuResponse | None:
        """SKU 情報を更新する。渡されたフィールドのみ更新"""
        sku = await self._get_sku_orm(sku_id)
        if sku is None:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(sku, key, value)

        try:
            await self.db.flush()
        except sa_exc.IntegrityError as e:
            raise DatabaseException(
                message="SKUコードが重複しています",
                detail=str(e),
                original_exception=e,
            ) from e
        await self.db.refresh(sku)
        return SkuResponse.model_validate(sku)

    async def delete_sku(self, sku_id: int) -> bool:
        """SKU を削除する"""
        sku = await self._get_sku_orm(sku_id)
        if sku is None:
            return False
        await self.db.delete(sku)
        await self.db.flush()
        return True

    async def update_stock(self, sku_id: int, quantity: int) -> SkuResponse | None:
        """SKU の在庫を指定された数量に設定する"""
        sku = await self._get_sku_orm(sku_id)
        if sku is None:
            return None
        sku.stock = quantity
        await self.db.flush()
        await self.db.refresh(sku)
        return SkuResponse.model_validate(sku)

    async def _get_sku_orm(self, sku_id: int) -> Sku | None:
        """内部メソッド: 更新/削除用に ORM オブジェクトを取得する"""
        stmt = select(Sku).where(Sku.id == sku_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
