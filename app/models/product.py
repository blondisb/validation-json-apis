from sqlalchemy import Column, Integer, String, Text, Boolean, DECIMAL, DateTime, JSON
from sqlalchemy.sql import func
from app.models.base import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    sku = Column(String(20), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    price_amount = Column(DECIMAL(10, 2), nullable=False)
    price_currency = Column(String(3), nullable=False)
    tags = Column(JSON, default=list)
    dimensions = Column(JSON, nullable=True)
    images = Column(JSON, default=list)
    in_stock = Column(Boolean, default=True)
    category_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())