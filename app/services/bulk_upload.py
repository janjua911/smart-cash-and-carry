import pandas as pd
from decimal import Decimal
from sqlalchemy.orm import Session
from fastapi import UploadFile

from app.models.product import Product, StockStatus
from app.models.category import Category
from app.services.slug import unique_product_slug


def process_bulk_upload(db: Session, file: UploadFile) -> dict:
    """Process Excel/CSV file and update/create products."""
    
    result = {
        "created": 0,
        "updated": 0,
        "errors": [],
        "skipped": 0
    }
    
    # Read file
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file.file)
        else:
            df = pd.read_excel(file.file)
    except Exception as e:
        result["errors"].append(f"Failed to read file: {str(e)}")
        return result
    
    # Required columns check
    required = ['name', 'category', 'price', 'stock_quantity']
    missing = [col for col in required if col not in df.columns]
    if missing:
        result["errors"].append(f"Missing columns: {', '.join(missing)}")
        return result
    
    # Process each row
    for idx, row in df.iterrows():
        try:
            # Skip empty rows
            if pd.isna(row.get('name')) or not str(row.get('name')).strip():
                result["skipped"] += 1
                continue
            
            name = str(row.get('name')).strip()
            category_name = str(row.get('category')).strip()
            price = float(row.get('price', 0))
            stock_qty = int(row.get('stock_quantity', 0))
            
            # Get or create category
            category = db.query(Category).filter(
                Category.name.ilike(category_name)
            ).first()
            
            if not category:
                # Create new category
                from app.services.slug import unique_category_slug
                category = Category(
                    name=category_name,
                    slug=unique_category_slug(db, category_name),
                    is_active=True
                )
                db.add(category)
                db.flush()
                result["created"] += 1  # Category created
            
            # Check if product exists
            product_id = row.get('product_id')
            product = None
            
            if product_id and not pd.isna(product_id):
                product = db.get(Product, int(product_id))
            
            if not product:
                # Try to find by name
                product = db.query(Product).filter(
                    Product.name.ilike(name)
                ).first()
            
            if product:
                # ✅ Update existing product
                product.price = Decimal(str(price))
                product.stock_quantity = stock_qty
                product.category_id = category.id
                
                # Update compare_at_price if provided
                if 'compare_at_price' in df.columns and not pd.isna(row.get('compare_at_price')):
                    product.compare_at_price = Decimal(str(row.get('compare_at_price')))
                
                # Update unit if provided
                if 'unit' in df.columns and not pd.isna(row.get('unit')):
                    product.unit = str(row.get('unit')).strip()
                
                # Update description if provided
                if 'description' in df.columns and not pd.isna(row.get('description')):
                    product.description = str(row.get('description')).strip()
                
                # Update is_active if provided
                if 'is_active' in df.columns and not pd.isna(row.get('is_active')):
                    val = str(row.get('is_active')).strip().lower()
                    product.is_active = val in {'yes', 'true', '1', 'active'}
                
                # Update slug if provided
                if 'slug' in df.columns and not pd.isna(row.get('slug')):
                    product.slug = unique_product_slug(db, str(row.get('slug')).strip(), product.id)
                
                # Auto update stock status
                if stock_qty > 0:
                    product.stock_status = StockStatus.IN_STOCK
                else:
                    product.stock_status = StockStatus.OUT_OF_STOCK
                
                result["updated"] += 1
                
            else:
                # ✅ Create new product
                slug = str(row.get('slug')).strip() if 'slug' in df.columns and not pd.isna(row.get('slug')) else name
                
                product = Product(
                    name=name,
                    slug=unique_product_slug(db, slug, None),
                    category_id=category.id,
                    price=Decimal(str(price)),
                    stock_quantity=stock_qty,
                    stock_status=StockStatus.IN_STOCK if stock_qty > 0 else StockStatus.OUT_OF_STOCK,
                    is_active=True,
                    unit=str(row.get('unit', '1 item')).strip() if 'unit' in df.columns else '1 item',
                    description=str(row.get('description', '')).strip() if 'description' in df.columns else '',
                )
                
                if 'compare_at_price' in df.columns and not pd.isna(row.get('compare_at_price')):
                    product.compare_at_price = Decimal(str(row.get('compare_at_price')))
                
                db.add(product)
                db.flush()
                result["created"] += 1
                
        except Exception as e:
            result["errors"].append(f"Row {idx + 2}: {str(e)}")
            continue
    
    db.commit()
    return result