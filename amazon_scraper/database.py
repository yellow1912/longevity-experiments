"""
SQLite Database Module
Schema, connection management, and CRUD operations for scraped product data.
"""
import json
import os
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import DATABASE_SETTINGS

# Fields stored as JSON text in the products table
_JSON_FIELDS = (
    "description", "images", "best_sellers_rank",
    "product_details", "product_overview", "videos", "validation",
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    asin            TEXT PRIMARY KEY,
    category        TEXT NOT NULL,
    title           TEXT,
    price           TEXT,
    brand           TEXT,
    rating          TEXT,
    review_count    INTEGER,
    affiliate_url   TEXT,
    description     TEXT,   -- JSON
    images          TEXT,   -- JSON
    best_sellers_rank TEXT, -- JSON
    product_details TEXT,   -- JSON
    product_overview TEXT,  -- JSON
    videos          TEXT,   -- JSON
    validation      TEXT,   -- JSON
    scraped_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_products_category   ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_rating     ON products(rating);
CREATE INDEX IF NOT EXISTS idx_products_updated_at ON products(updated_at);

CREATE TABLE IF NOT EXISTS reviews (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    asin        TEXT NOT NULL REFERENCES products(asin),
    rating      TEXT,
    text        TEXT,
    date        TEXT,
    verified    INTEGER,
    reviewer    TEXT,
    UNIQUE(asin, reviewer, date)
);

CREATE INDEX IF NOT EXISTS idx_reviews_asin ON reviews(asin);

CREATE TABLE IF NOT EXISTS scrape_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    asin        TEXT NOT NULL,
    scraped_at  TEXT NOT NULL,
    success     INTEGER NOT NULL,
    error       TEXT
);

CREATE INDEX IF NOT EXISTS idx_scrape_history_asin ON scrape_history(asin);
"""


class Database:
    """Thread-safe SQLite database manager with WAL mode."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DATABASE_SETTINGS["db_path"]
        self._local = threading.local()
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        # Create schema using a temporary connection
        conn = self._connect()
        conn.executescript(_SCHEMA)
        conn.commit()

    def _connect(self) -> sqlite3.Connection:
        """Get or create a per-thread connection."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return conn

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def upsert_product(self, product: Dict[str, Any]) -> None:
        """Insert or update a product, preserving original scraped_at."""
        conn = self._connect()
        now = datetime.now(timezone.utc).isoformat()

        # Check for existing scraped_at
        row = conn.execute(
            "SELECT scraped_at FROM products WHERE asin = ?",
            (product["asin"],),
        ).fetchone()
        scraped_at = row["scraped_at"] if row else product.get("scraped_at", now)

        # Serialise JSON fields
        data = dict(product)
        for field in _JSON_FIELDS:
            if field in data and not isinstance(data[field], str):
                data[field] = json.dumps(data[field])

        conn.execute(
            """INSERT OR REPLACE INTO products
               (asin, category, title, price, brand, rating, review_count,
                affiliate_url, description, images, best_sellers_rank,
                product_details, product_overview, videos, validation,
                scraped_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                data["asin"],
                data.get("category", ""),
                data.get("title"),
                data.get("price"),
                data.get("brand"),
                data.get("rating"),
                data.get("review_count"),
                data.get("affiliate_url"),
                data.get("description"),
                data.get("images"),
                data.get("best_sellers_rank"),
                data.get("product_details"),
                data.get("product_overview"),
                data.get("videos"),
                data.get("validation"),
                scraped_at,
                now,
            ),
        )
        conn.commit()

    def insert_reviews(self, asin: str, reviews: List[Dict[str, Any]]) -> int:
        """Insert reviews, ignoring duplicates. Returns count of new rows."""
        conn = self._connect()
        inserted = 0
        for r in reviews:
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO reviews
                       (asin, rating, text, date, verified, reviewer)
                       VALUES (?,?,?,?,?,?)""",
                    (
                        asin,
                        r.get("rating"),
                        r.get("text"),
                        r.get("date"),
                        1 if r.get("verified") else 0,
                        r.get("reviewer"),
                    ),
                )
                inserted += conn.total_changes  # approximate
            except sqlite3.IntegrityError:
                pass
        conn.commit()
        return inserted

    def log_scrape(self, asin: str, success: bool, error: str = None) -> None:
        """Append to scrape_history."""
        conn = self._connect()
        conn.execute(
            "INSERT INTO scrape_history (asin, scraped_at, success, error) VALUES (?,?,?,?)",
            (asin, datetime.now(timezone.utc).isoformat(), 1 if success else 0, error),
        )
        conn.commit()

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def _deserialize_row(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert a Row to dict, deserializing JSON fields."""
        d = dict(row)
        for field in _JSON_FIELDS:
            if field in d and isinstance(d[field], str):
                try:
                    d[field] = json.loads(d[field])
                except (json.JSONDecodeError, TypeError):
                    pass
        return d

    def get_product(self, asin: str) -> Optional[Dict[str, Any]]:
        """Get a single product with its reviews."""
        conn = self._connect()
        row = conn.execute("SELECT * FROM products WHERE asin = ?", (asin,)).fetchone()
        if not row:
            return None
        product = self._deserialize_row(row)
        product["reviews"] = [
            dict(r)
            for r in conn.execute(
                "SELECT rating, text, date, verified, reviewer FROM reviews WHERE asin = ?",
                (asin,),
            ).fetchall()
        ]
        # Convert verified back to bool
        for r in product["reviews"]:
            r["verified"] = bool(r["verified"])
        return product

    def get_products(
        self,
        category: str = None,
        min_rating: float = None,
        brand: str = None,
        search: str = None,
        sort_by: str = "updated_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get products with filtering and pagination.
        Returns (products_list, total_count).
        """
        conn = self._connect()
        conditions = []
        params: list = []

        if category:
            conditions.append("category = ?")
            params.append(category)
        if min_rating is not None:
            conditions.append("CAST(rating AS REAL) >= ?")
            params.append(min_rating)
        if brand:
            conditions.append("brand LIKE ?")
            params.append(f"%{brand}%")
        if search:
            conditions.append("(title LIKE ? OR brand LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Validate sort
        allowed_sorts = {"updated_at", "rating", "review_count", "title", "price", "scraped_at"}
        if sort_by not in allowed_sorts:
            sort_by = "updated_at"
        order = "ASC" if order.lower() == "asc" else "DESC"

        # Total count
        total = conn.execute(
            f"SELECT COUNT(*) as cnt FROM products {where}", params
        ).fetchone()["cnt"]

        # Paginated results
        offset = (page - 1) * page_size
        rows = conn.execute(
            f"SELECT * FROM products {where} ORDER BY {sort_by} {order} LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

        products = [self._deserialize_row(r) for r in rows]
        return products, total

    def get_reviews_for_product(self, asin: str) -> List[Dict[str, Any]]:
        conn = self._connect()
        rows = conn.execute(
            "SELECT rating, text, date, verified, reviewer FROM reviews WHERE asin = ?",
            (asin,),
        ).fetchall()
        reviews = [dict(r) for r in rows]
        for r in reviews:
            r["verified"] = bool(r["verified"])
        return reviews

    def get_categories(self) -> List[Dict[str, Any]]:
        """Return categories with product counts."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT category, COUNT(*) as count FROM products GROUP BY category ORDER BY count DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> Dict[str, Any]:
        """Return overall database statistics."""
        conn = self._connect()
        total_products = conn.execute("SELECT COUNT(*) as cnt FROM products").fetchone()["cnt"]
        total_reviews = conn.execute("SELECT COUNT(*) as cnt FROM reviews").fetchone()["cnt"]
        categories = conn.execute("SELECT COUNT(DISTINCT category) as cnt FROM products").fetchone()["cnt"]
        last_scrape = conn.execute(
            "SELECT MAX(updated_at) as last FROM products"
        ).fetchone()["last"]

        threshold = DATABASE_SETTINGS["stale_threshold_days"]
        cutoff = (datetime.now(timezone.utc) - timedelta(days=threshold)).isoformat()
        stale_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM products WHERE updated_at < ?", (cutoff,)
        ).fetchone()["cnt"]

        return {
            "total_products": total_products,
            "total_reviews": total_reviews,
            "categories": categories,
            "last_scrape_time": last_scrape,
            "stale_count": stale_count,
        }

    def get_stale_asins(self, threshold_days: int = None) -> List[Tuple[str, str]]:
        """Return (asin, category) pairs where updated_at is older than threshold."""
        days = threshold_days or DATABASE_SETTINGS["stale_threshold_days"]
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        conn = self._connect()
        rows = conn.execute(
            "SELECT asin, category FROM products WHERE updated_at < ? ORDER BY updated_at ASC",
            (cutoff,),
        ).fetchall()
        return [(r["asin"], r["category"]) for r in rows]

    def get_all_asins(self) -> set:
        """Return all ASINs in the database."""
        conn = self._connect()
        rows = conn.execute("SELECT asin FROM products").fetchall()
        return {r["asin"] for r in rows}


# ------------------------------------------------------------------
# One-time migration from JSON files
# ------------------------------------------------------------------

def import_json_to_db(data_dir: str = None, db_path: str = None) -> None:
    """Import existing JSON files into the database."""
    from .config import OUTPUT_SETTINGS

    data_dir = data_dir or OUTPUT_SETTINGS["data_dir"]
    db = Database(db_path)

    if not os.path.exists(data_dir):
        print(f"Data directory '{data_dir}' does not exist. Nothing to import.")
        return

    imported = 0
    skipped = 0

    for category_dir in sorted(Path(data_dir).iterdir()):
        if not category_dir.is_dir():
            continue

        category = category_dir.name
        json_files = sorted(category_dir.glob("*.json"))
        print(f"Importing {len(json_files)} products from '{category}'...")

        for json_file in json_files:
            try:
                with open(json_file) as f:
                    product = json.load(f)

                # Ensure required fields
                if "asin" not in product:
                    product["asin"] = json_file.stem
                if "category" not in product:
                    product["category"] = category

                reviews = product.pop("reviews", [])
                db.upsert_product(product)
                if reviews:
                    db.insert_reviews(product["asin"], reviews)
                db.log_scrape(product["asin"], success=True)
                imported += 1

            except Exception as e:
                print(f"  Error importing {json_file.name}: {e}")
                skipped += 1

    print(f"\nImport complete: {imported} products imported, {skipped} skipped.")
    print(f"Database: {db.db_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database utilities")
    parser.add_argument("--import", dest="do_import", action="store_true",
                        help="Import existing JSON files into the database")
    parser.add_argument("--db-path", type=str, default=None,
                        help="Override database path")
    parser.add_argument("--data-dir", type=str, default=None,
                        help="Override data directory for import")
    args = parser.parse_args()

    if args.do_import:
        import_json_to_db(data_dir=args.data_dir, db_path=args.db_path)
    else:
        parser.print_help()
