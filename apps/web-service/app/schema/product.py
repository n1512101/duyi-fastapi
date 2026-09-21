from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class CategoryBrief(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class SkuBrief(BaseModel):
    id: int
    sku_code: str
    price: Decimal
    stock: int
    attrs: dict[str, Any]
    image_url: str

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200, description="商品名")
    description: str = Field(default="", description="商品説明")
    brand: str | None = Field(default=None, max_length=100, description="ブランド")
    category_ids: list[int] = Field(default_factory=list, description="関連カテゴリIDリスト")


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200, description="商品名")
    description: str | None = Field(default=None, description="商品説明")
    brand: str | None = Field(default=None, max_length=100, description="ブランド")
    category_ids: list[int] | None = Field(default=None, description="関連カテゴリIDリスト")


class ProductBrief(BaseModel):
    """商品の簡易情報。リスト表示やネスト参照に使用"""
    id: int
    name: str
    description: str
    brand: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductResponse(BaseModel):
    id: int
    name: str
    description: str
    brand: str | None
    created_at: datetime
    updated_at: datetime
    categories: list[CategoryBrief] = []
    skus: list[SkuBrief] = []

    model_config = {"from_attributes": True}
