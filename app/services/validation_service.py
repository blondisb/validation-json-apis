from sqlalchemy.orm import Session
from typing import Dict, Any
from app.models.product import Product
from app.schemas.product import ProductCreate

class ValidationService:
    def __init__(self, db: Session):
        self.db = db

    async def validate_business_constraints(self, product_data: ProductCreate) -> Dict[str, Any]:
        """Validaciones que requieren acceso a BD"""
        errors = {}
        
        # Verificar SKU único
        existing_sku = self.db.query(Product).filter_by(sku=product_data.sku).first()
        if existing_sku:
            errors['sku'] = 'SKU ya existe en el sistema'
        
        # Verificar nombre único
        existing_name = self.db.query(Product).filter_by(name=product_data.name).first()
        if existing_name:
            errors['name'] = 'Ya existe un producto con este nombre'
        
        # Validaciones adicionales de negocio aquí
        
        return errors