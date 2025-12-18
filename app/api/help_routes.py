# # app/api/help_routes.py
# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from typing import List, Optional

# from app.db import SessionLocal
# from app.auth import get_current_user_row
# from app.schemas import BaseModel
# from app.crud import crud

# # ==========================
# # Pydantic Schemas for API
# # ==========================
# class HelpCategoryOut(BaseModel):
#     id: int
#     name: str
#     description: Optional[str]

#     class Config:
#         orm_mode = True


# class HelpArticleOut(BaseModel):
#     id: int
#     category_id: int
#     title: str
#     content: str
#     is_active: bool

#     class Config:
#         orm_mode = True


# # ==========================
# # FastAPI Router
# # ==========================
# router = APIRouter(
#     prefix="/api/help",
#     tags=["Help"]
# )


# # -----------------------------
# # Dependency: DB session
# # -----------------------------
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


# # -----------------------------
# # GET ALL CATEGORIES
# # -----------------------------
# @router.get("/categories", response_model=List[HelpCategoryOut])
# def list_categories(db: Session = Depends(get_db)):
#     categories = crud.list_help_categories(db)
#     return categories


# # -----------------------------
# # GET ARTICLES (optionally by category)
# # -----------------------------
# @router.get("/articles", response_model=List[HelpArticleOut])
# def list_articles(category_id: Optional[int] = None, db: Session = Depends(get_db)):
#     articles = crud.list_help_articles(db, category_id=category_id)
#     return articles


# # -----------------------------
# # GET SINGLE ARTICLE
# # -----------------------------
# @router.get("/articles/{article_id}", response_model=HelpArticleOut)
# def get_article(article_id: int, db: Session = Depends(get_db)):
#     article = crud.get_help_article(db, article_id)
#     if not article:
#         raise HTTPException(status_code=404, detail="Help article not found")
#     return article


# # -----------------------------
# # ADMIN: GET ALL ARTICLES (including inactive)
# # -----------------------------
# @router.get("/admin/articles", response_model=List[HelpArticleOut])
# def admin_list_articles(user=Depends(get_current_user_row), db: Session = Depends(get_db)):
#     # Only superusers can access
#     if not user.get("is_superuser"):
#         raise HTTPException(status_code=403, detail="Admin access required")
#     articles = crud.list_help_articles(db, category_id=None, active_only=False)
#     return articles



# app/api/help_routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from pydantic import BaseModel   # ✅ FIX 1

from app.db import SessionLocal
from app.auth import get_current_user_row
from app import crud             # ✅ FIX 2


# ==========================
# Pydantic Schemas
# ==========================
class HelpCategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        orm_mode = True


class HelpArticleOut(BaseModel):
    id: int
    category_id: int
    title: str
    content: str
    is_active: bool

    class Config:
        orm_mode = True


# ==========================
# Router
# ==========================
router = APIRouter(
    prefix="/help",
    tags=["Help"]
)


# ==========================
# DB Dependency
# ==========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================
# PUBLIC APIs
# ==========================
@router.get("/categories", response_model=List[HelpCategoryOut])
def list_categories(db: Session = Depends(get_db)):
    return crud.list_help_categories(db)


@router.get("/articles", response_model=List[HelpArticleOut])
def list_articles(
    category_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return crud.list_help_articles(db, category_id=category_id)


@router.get("/articles/{article_id}", response_model=HelpArticleOut)
def get_article(article_id: int, db: Session = Depends(get_db)):
    article = crud.get_help_article(db, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Help article not found")
    return article


# ==========================
# ADMIN APIs
# ==========================
@router.get("/admin/articles", response_model=List[HelpArticleOut])
def admin_list_articles(
    user=Depends(get_current_user_row),
    db: Session = Depends(get_db),
):
    if not user.get("is_superuser"):
        raise HTTPException(status_code=403, detail="Admin access required")

    return crud.list_help_articles(
        db,
        category_id=None,
        active_only=False
    )
