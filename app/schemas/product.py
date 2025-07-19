from pydantic import BaseModel, Field, HttpUrl, validator, root_validator
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

class ImageSchema(BaseModel):
    url: HttpUrl = Field(..., description="URL válida de la imagen")
    alt_text: str = Field(..., min_length=1, max_length=100)

class PriceSchema(BaseModel):
    amount: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)
    currency: str = Field(..., regex=r"^[A-Z]{3}$")
    
    @validator('currency')
    def validate_currency_code(cls, v):
        valid_currencies = {'USD', 'EUR', 'COP', 'GBP', 'JPY', 'CAD', 'AUD'}
        if v not in valid_currencies:
            raise ValueError(f'Moneda {v} no válida. Usar: {", ".join(valid_currencies)}')
        return v

class DimensionsSchema(BaseModel):
    width: float = Field(..., gt=0)
    height: float = Field(..., gt=0) 
    depth: float = Field(..., gt=0)
    
    @root_validator
    def validate_dimensions(cls, values):
        max_dimension = 500  # cm
        for dim_name, dim_value in values.items():
            if dim_value and dim_value > max_dimension:
                raise ValueError(f'{dim_name} no puede exceder {max_dimension}cm')
        return values

class ProductBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    sku: str = Field(..., regex=r"^[A-Z0-9\-]{5,20}$")
    description: Optional[str] = Field(None, max_length=500)
    price: PriceSchema
    tags: List[str] = Field(default_factory=list)
    dimensions: Optional[DimensionsSchema] = None
    images: Optional[List[ImageSchema]] = Field(default_factory=list)
    in_stock: bool = Field(True)
    category_id: Optional[int] = Field(None, gt=0)

class ProductCreate(ProductBase):
    @validator('name')
    def validate_name(cls, v):
        forbidden_words = {'producto', 'artículo', 'item', 'thing', 'objeto'}
        if v.lower().strip() in forbidden_words:
            raise ValueError('El nombre no puede ser una palabra genérica')
        return v.strip().title()
    
    @validator('tags', each_item=True)
    def validate_tags(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError('Los tags no pueden estar vacíos')
        if len(v) > 30:
            raise ValueError('Cada tag debe tener máximo 30 caracteres')
        return v.strip().lower()
    
    @validator('tags')
    def validate_tags_uniqueness(cls, v):
        if len(v) != len(set(v)):
            raise ValueError('No puede haber tags duplicados')
        if len(v) > 10:
            raise ValueError('Máximo 10 tags permitidos')
        return v
    
    @root_validator
    def validate_business_rules(cls, values):
        in_stock = values.get('in_stock')
        price = values.get('price')
        dimensions = values.get('dimensions')
        
        if not in_stock and price and price.amount > 1000:
            raise ValueError('Productos fuera de stock no pueden tener precio mayor a $1000')
        
        if dimensions:
            volume = dimensions.width * dimensions.height * dimensions.depth
            if volume > 100000 and not values.get('images'):
                raise ValueError('Productos grandes requieren al menos una imagen')
        
        return values

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    price: Optional[PriceSchema] = None
    tags: Optional[List[str]] = None
    dimensions: Optional[DimensionsSchema] = None
    images: Optional[List[ImageSchema]] = None
    in_stock: Optional[bool] = None
    category_id: Optional[int] = Field(None, gt=0)

class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True