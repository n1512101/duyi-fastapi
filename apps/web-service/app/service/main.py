"""業務ロジック層のデモスクリプト。学習順に service 層の主要な使い方を示す。

実行方法:
    uv run --package web-service python apps/web-service/app/service/main.py
"""

import asyncio
from decimal import Decimal

from sqlalchemy import delete, text

from app.core.database import get_session_factory
from app.model.association import product_category
from app.model.category import Category
from app.model.product import Product
from app.model.sku import Sku
from app.schema.category import CategoryCreate
from app.schema.product import ProductCreate, ProductUpdate
from app.schema.sku import SkuCreate
from app.service.category_service import CategoryService
from app.service.product_service import ProductService
from app.service.sku_service import SkuService


async def main():
    async with get_session_factory()() as session:
        # ========== 0. 旧データを削除して冪等性を保証 ==========
        await session.execute(delete(Sku))
        await session.execute(delete(product_category))
        await session.execute(delete(Product))
        await session.execute(delete(Category))
        await session.execute(text("ALTER SEQUENCE sku_id_seq RESTART WITH 1"))
        await session.execute(text("ALTER SEQUENCE product_id_seq RESTART WITH 1"))
        await session.execute(text("ALTER SEQUENCE category_id_seq RESTART WITH 1"))
        await session.flush()

        # ========== 1. カテゴリを作成 ==========
        print("========== 1. カテゴリを作成 ==========")
        category_svc = CategoryService(session)
        c1 = await category_svc.create_category(
            CategoryCreate(name="電子製品", description="スマホ、パソコンなど")
        )
        c2 = await category_svc.create_category(CategoryCreate(name="書籍"))
        c3 = await category_svc.create_category(CategoryCreate(name="衣類"))
        print(
            f"カテゴリを作成: [{c1.id}] {c1.name}, [{c2.id}] {c2.name}, [{c3.id}] {c3.name}"
        )

        # ========== 2. カテゴリをページングで取得 ==========
        print("\n========== 2. カテゴリをページングで取得 ==========")
        result = await category_svc.list_categories(page=1, page_size=10)
        print(f"合計 {result.total} 件, 現在のページ {result.page}/{result.page_size} 件")
        for cat in result.items:
            print(f"  [{cat.id}] {cat.name}")

        # ========== 3. 商品を作成してカテゴリに紐づけ ==========
        print("\n========== 3. 商品を作成してカテゴリに紐づけ ==========")
        product_svc = ProductService(session)
        p1 = await product_svc.create_product(
            ProductCreate(
                name="iPhone 16",
                description="Apple 最新のスマートフォン",
                brand="Apple",
                category_ids=[c1.id],
            )
        )
        p2 = await product_svc.create_product(
            ProductCreate(
                name="MacBook Pro",
                description="Apple のノートパソコン",
                brand="Apple",
                category_ids=[c1.id],
            )
        )
        p3 = await product_svc.create_product(
            ProductCreate(
                name="Python入門講座",
                description="初心者から学ぶPython",
                brand="技術評論社",
                category_ids=[c2.id],
            )
        )
        print(
            f"商品を作成: [{p1.id}] {p1.name}, [{p2.id}] {p2.name}, [{p3.id}] {p3.name}"
        )

        # ========== 4. SKU を作成 ==========
        print("\n========== 4. SKU を作成 ==========")
        sku_svc = SkuService(session)
        s1 = await sku_svc.create_sku(
            p1.id,
            SkuCreate(
                sku_code="IP16-128-BLK",
                price=Decimal("6999.00"),
                stock=100,
                attrs={"色": "ブラック", "ストレージ": "128G"},
                image_url="/images/ip16-blk.jpg",
            ),
        )
        assert s1 is not None
        s2 = await sku_svc.create_sku(
            p1.id,
            SkuCreate(
                sku_code="IP16-256-WHT",
                price=Decimal("7999.00"),
                stock=50,
                attrs={"色": "ホワイト", "ストレージ": "256G"},
                image_url="/images/ip16-wht.jpg",
            ),
        )
        assert s2 is not None
        s3 = await sku_svc.create_sku(
            p2.id,
            SkuCreate(
                sku_code="MBP14-M3-16G",
                price=Decimal("12999.00"),
                stock=30,
                attrs={"画面サイズ": "14インチ", "チップ": "M3", "メモリ": "16G"},
                image_url="/images/mbp14.jpg",
            ),
        )
        assert s3 is not None
        print(
            f"SKU を作成: [{s1.id}] {s1.sku_code} ¥{s1.price}, "
            f"[{s2.id}] {s2.sku_code} ¥{s2.price}, [{s3.id}] {s3.sku_code} ¥{s3.price}"
        )

        # ========== 5. 商品詳細を取得 ==========
        print("\n========== 5. 商品詳細を取得 ==========")
        detail = await product_svc.get_product(p1.id)
        assert detail is not None
        print(f"商品: {detail.name}")
        print(f"  カテゴリ: {[c.name for c in detail.categories]}")
        print(f"  SKU数: {len(detail.skus)}")
        for sku in detail.skus:
            print(f"    {sku.sku_code} | ¥{sku.price} | 在庫:{sku.stock} | {sku.attrs}")

        # ========== 6. カテゴリで商品を検索 ==========
        print("\n========== 6. カテゴリで商品を検索 ==========")
        result = await product_svc.list_products(
            category_id=c1.id, page=1, page_size=10
        )
        print(f"「{c1.name}」カテゴリの商品は合計 {result.total} 件:")
        for p in result.items:
            print(f"  [{p.id}] {p.name} ({p.brand}) | {p.description[:20]}")

        # ========== 7. キーワードで商品を検索 ==========
        print("\n========== 7. キーワード'Python'で商品を検索 ==========")
        result = await product_svc.list_products(keyword="Python", page=1, page_size=10)
        print(f"'Python' に一致する商品は合計 {result.total} 件:")
        for p in result.items:
            print(f"  [{p.id}] {p.name}")

        # ========== 8. SKU の在庫を更新 ==========
        print("\n========== 8. SKU の在庫を更新 ==========")
        updated_sku = await sku_svc.update_stock(s1.id, 80)
        assert updated_sku is not None
        print(f"{s1.sku_code} 在庫: {s1.stock} → {updated_sku.stock}")

        # ========== 9. 商品情報を更新 ==========
        print("\n========== 9. 商品情報を更新 ==========")
        updated = await product_svc.update_product(
            p2.id,
            ProductUpdate(
                description="2024年モデル MacBook Pro M3 チップ搭載ノートパソコン",
            ),
        )
        assert updated is not None
        print(f"更新後: {updated.name} → {updated.description}")

        # ========== 10. カテゴリ詳細を取得（商品リストを含む） ==========
        print("\n========== 10. カテゴリ詳細を取得 ==========")
        detail = await category_svc.get_category(c1.id)
        assert detail is not None
        print(f"カテゴリ「{detail.name}」には {len(detail.products)} 件の商品があります:")
        for p in detail.products:
            print(f"  [{p.id}] {p.name}")

        await session.commit()
        print("\n========== 全デモ完了 ==========")


if __name__ == "__main__":
    asyncio.run(main())
