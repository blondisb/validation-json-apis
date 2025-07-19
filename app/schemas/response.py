from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class BaseResponse(BaseModel):
    success: bool = True
    message: str
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    errors: Optional[Dict[str, Any]] = None
    detail: Optional[str] = None

class ValidationResponse(BaseModel):
    valid: bool
    errors: Optional[Dict[str, Any]] = None
    message: str

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int