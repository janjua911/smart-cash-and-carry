from decimal import Decimal

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models.admin import Admin
from app.models.category import Category
from app.models.product import Product, StockStatus
from app.services.slug import slugify


SEED_PRODUCTS = [
    ("Fresh Vine Tomatoes", "Fresh Produce", "500 g pack", "179", "220", 40),
    ("Pure Farm Milk", "Dairy & Eggs", "1 litre", "295", None, 25),
    ("Artisan Sourdough", "Bakery", "400 g loaf", "399", "460", 12),
    ("Premium Basmati Rice", "Pantry", "1 kg bag", "489", "550", 30),
    ("Extra Virgin Olive Oil", "Pantry", "500 ml bottle", "1249", "1399", 14),
    ("Classic Ground Coffee", "Beverages", "250 g pack", "749", None, 18),
    ("Home Cleaning Essentials", "Home Care", "4-piece set", "1199", "1350", 9),
    ("Hydrating Body Care", "Personal Care", "200 ml tube", "599", None, 16),
]


def run_seed() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        admin = db.scalar(select(Admin).where(Admin.email == settings.ADMIN_EMAIL.lower()))
        if not admin:
            db.add(
                Admin(
                    name="AI Fatah Admin",
                    email=settings.ADMIN_EMAIL.lower(),
                    password_hash=hash_password(settings.ADMIN_PASSWORD),
                )
            )

        category_names = sorted({item[1] for item in SEED_PRODUCTS})
        categories: dict[str, Category] = {}
        for name in category_names:
            category = db.scalar(select(Category).where(Category.name == name))
            if not category:
                category = Category(name=name, slug=slugify(name))
                db.add(category)
                db.flush()
            categories[name] = category

        for name, category_name, unit, price, compare_price, quantity in SEED_PRODUCTS:
            if db.scalar(select(Product).where(Product.slug == slugify(name))):
                continue
            db.add(
                Product(
                    name=name,
                    slug=slugify(name),
                    category_id=categories[category_name].id,
                    description=f"Quality {name.lower()} selected for the AI Fatah online store.",
                    unit=unit,
                    price=Decimal(price),
                    compare_at_price=Decimal(compare_price) if compare_price else None,
                    stock_quantity=quantity,
                    stock_status=StockStatus.IN_STOCK,
                    is_active=True,
                    is_featured=True,
                )
            )
        db.commit()

    print("Seed complete.")
    print(f"Admin email: {settings.ADMIN_EMAIL}")
    print("Admin password: value from ADMIN_PASSWORD in your .env file")


if __name__ == "__main__":
    run_seed()
