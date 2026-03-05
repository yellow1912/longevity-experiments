"""
Read-Only REST API
FastAPI application exposing scraped product data.
"""
import math
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from .database import Database

app = FastAPI(
    title="Amazon Supplement Data API",
    description="Read-only API for scraped Amazon supplement product data",
    version="1.0.0",
)

_db: Optional[Database] = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db


@app.get("/products")
def list_products(
    category: Optional[str] = None,
    min_rating: Optional[float] = None,
    brand: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "updated_at",
    order: str = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List products with filtering, sorting, and pagination."""
    products, total = get_db().get_products(
        category=category,
        min_rating=min_rating,
        brand=brand,
        search=search,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size,
    )
    return {
        "products": products,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
    }


@app.get("/products/{asin}")
def get_product(asin: str):
    """Get a single product with its reviews."""
    product = get_db().get_product(asin)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {asin} not found")
    return product


@app.get("/categories")
def list_categories():
    """List all categories with product counts."""
    return get_db().get_categories()


@app.get("/stats")
def get_stats():
    """Get overall database statistics."""
    return get_db().get_stats()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("amazon_scraper.api:app", host="0.0.0.0", port=8000, reload=False)
