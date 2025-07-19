from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse

class ProductService:
    def __init__(self, db: Session):
        self.db = db

    async def create_product(self, product_data: ProductCreate) -> ProductResponse:
        """Crear un nuevo producto"""
        db_product = Product(
            name=product_data.name,
            sku=product_data.sku,
            description=product_data.description,
            price_amount=product_data.price.amount,
            price_currency=product_data.price.currency,
            tags=product_data.tags,
            dimensions=product_data.dimensions.dict() if product_data.dimensions else None,
            images=[img.dict() for img in product_data.images] if product_data.images else [],
            in_stock=product_data.in_stock,
            category_id=product_data.category_id
        )
        
        self.db.add(db_product)
        self.db.commit()
        self.db.refresh(db_product)
        
        return self._to_response(db_product)

    async def get_products(self, skip: int = 0, limit: int = 100) -> List[ProductResponse]:
        """Obtener lista de productos"""
        products = self.db.query(Product).offset(skip).limit(limit).all()
        return [self._to_response(product) for product in products]

    async def get_product_by_id(self, product_id: int) -> Optional[ProductResponse]:
        """Obtener producto por ID"""
        product = self.db.query(Product).filter(Product.id == product_id).first()
        return self._to_response(product) if product else None

    def _to_response(self, db_product: Product) -> ProductResponse:
        """Convertir modelo de DB a esquema de respuesta"""
        return ProductResponse(
            id=db_product.id,
            name=db_product.name,
            sku=db_product.sku,
            description=db_product.description,
            price={
                "amount": db_product.price_amount,
                "currency": db_product.price_currency
            },
            tags=db_product.tags or [],
            dimensions=db_product.dimensions,
            images=db_product.images or [],
            in_stock=db_product.in_stock,
            category_id=db_product.category_id,
            created_at=db_product.created_at,
            updated_at=db_product.updated_at
        )