from pydantic import BaseModel, Field

from app.schema.product import ProductBrief


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50, description="カテゴリ名")
    description: str = Field(default="", description="カテゴリ説明")


class CategoryUpdate(BaseModel):
    name: str | None = Field(
        default=None, min_length=1, max_length=50, description="カテゴリ名"
    )
    description: str | None = Field(default=None, description="カテゴリ説明")


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: str

    model_config = {"from_attributes": True}


class CategoryDetailResponse(BaseModel):
    """カテゴリ詳細。関連する商品リストを含む"""

    id: int
    name: str
    description: str
    products: list[ProductBrief] = []

    model_config = {"from_attributes": True}
