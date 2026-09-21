from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.exception import NotFoundException
from app.schema.category import (
    CategoryCreate,
    CategoryDetailResponse,
    CategoryResponse,
    CategoryUpdate,
)
from app.service.category_service import CategoryService

router = APIRouter(prefix="/api/categories", tags=["カテゴリ"])


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate, db: Annotated[AsyncSession, Depends(get_db)]
):
    return await CategoryService(db).create_category(data)


@router.get("")
async def list_categories(
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(default=1, ge=1, description="ページ番号"),
    page_size: int = Query(default=20, ge=1, le=100, description="1ページあたりの件数"),
):
    return await CategoryService(db).list_categories(page=page, page_size=page_size)


@router.get("/{category_id}", response_model=CategoryDetailResponse)
async def get_category(
    category_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await CategoryService(db).get_category(category_id)
    if result is None:
        raise NotFoundException(message="カテゴリが存在しません")
    return result


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await CategoryService(db).update_category(category_id, data)
    if result is None:
        raise NotFoundException(message="カテゴリが存在しません")
    return result


@router.delete("/{category_id}", status_code=204)
async def delete_category(
    category_id: int, db: Annotated[AsyncSession, Depends(get_db)]
):
    deleted = await CategoryService(db).delete_category(category_id)
    if not deleted:
        raise NotFoundException(message="カテゴリが存在しません")
