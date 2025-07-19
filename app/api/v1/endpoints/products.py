from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.schemas.response import ValidationResponse, ErrorResponse
from app.services.product_service import ProductService
from app.services.validation_service import ValidationService
from app.core.logging import logger

router = APIRouter()

@router.post(
    "/", 
    response_model=ProductResponse, 
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {"model": ErrorResponse, "description": "Error de validación"},
        409: {"model": ErrorResponse, "description": "Conflicto (SKU duplicado)"}
    }
)
async def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db)
):
    """Crear un nuevo producto con validación rigurosa"""
    try:
        product_service = ProductService(db)
        validation_service = ValidationService(db)
        
        # Validaciones de negocio adicionales
        business_errors = await validation_service.validate_business_constraints(product_data)
        if business_errors:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "Errores de validación de negocio",
                    "errors": business_errors
                }
            )
        
        # Crear producto
        product = await product_service.create_product(product_data)
        logger.info(f"Producto creado exitosamente: SKU {product.sku}")
        
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado creando producto: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.post("/validate", response_model=ValidationResponse)
async def validate_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db)
):
    """Validar datos del producto sin crearlo"""
    validation_service = ValidationService(db)
    business_errors = await validation_service.validate_business_constraints(product_data)
    
    return ValidationResponse(
        valid=len(business_errors) == 0,
        errors=business_errors if business_errors else None,
        message="Datos válidos" if not business_errors else "Se encontraron errores"
    )

@router.get("/", response_model=List[ProductResponse])
async def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Obtener lista de productos"""
    product_service = ProductService(db)
    return await product_service.get_products(skip=skip, limit=limit)

@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: Session = Depends(get_db)
):
    """Obtener un producto por ID"""
    product_service = ProductService(db)
    product = await product_service.get_product_by_id(product_id)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    
    return product