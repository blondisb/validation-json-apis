# app/api/deps.py - Dependencias centralizadas de FastAPI

from fastapi import Depends, HTTPException, status, Header, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, Generator, Annotated
from jose import JWTError, jwt
import redis
from datetime import datetime, timedelta

from app.config.database import SessionLocal
from app.config.settings import settings
from app.models.user import User  # Asumiendo que tienes un modelo User
from app.core.logging import logger

# =============================================================================
# DATABASE DEPENDENCIES
# =============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Dependencia para obtener sesión de base de datos
    Se usa en todos los endpoints que necesitan acceso a BD
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Error en sesión de BD: {e}")
        db.rollback()
        raise
    finally:
        db.close()

# Alias con tipo para mejor autocompletado
DatabaseSession = Annotated[Session, Depends(get_db)]

# =============================================================================
# AUTHENTICATION DEPENDENCIES
# =============================================================================

# Esquema de seguridad Bearer Token
security = HTTPBearer()

def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Obtener usuario actual desde el token JWT
    Valida el token y retorna el usuario autenticado
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificar el token JWT
        payload = jwt.decode(
            credentials.credentials, 
            settings.SECRET_KEY, 
            algorithms=["HS256"]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Buscar usuario en BD
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
        
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verificar que el usuario actual esté activo
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Usuario inactivo"
        )
    return current_user

def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Verificar que el usuario actual sea administrador
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos suficientes"
        )
    return current_user

# Aliases con tipos para mejor documentación
CurrentUser = Annotated[User, Depends(get_current_user)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]
AdminUser = Annotated[User, Depends(get_current_admin_user)]

# =============================================================================
# VALIDATION DEPENDENCIES
# =============================================================================

def validate_pagination(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(10, ge=1, le=100, description="Elementos por página")
) -> dict:
    """
    Validar parámetros de paginación
    """
    return {
        "skip": (page - 1) * size,
        "limit": size,
        "page": page,
        "size": size
    }

def validate_content_type(
    content_type: str = Header(..., alias="content-type")
) -> str:
    """
    Validar que el Content-Type sea application/json
    """
    if content_type != "application/json":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Content-Type debe ser application/json"
        )
    return content_type

def validate_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """
    Validar API Key para endpoints públicos
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key requerida"
        )
    
    # Validar contra API keys válidas (desde BD o configuración)
    valid_api_keys = settings.VALID_API_KEYS  # Lista de API keys válidas
    if x_api_key not in valid_api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key inválida"
        )
    
    return x_api_key

# =============================================================================
# CACHE DEPENDENCIES
# =============================================================================

def get_redis() -> redis.Redis:
    """
    Dependencia para obtener conexión a Redis
    """
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        decode_responses=True
    )

def get_cache_key(
    endpoint: str,
    user_id: Optional[int] = None,
    **params
) -> str:
    """
    Generar clave de cache consistente
    """
    key_parts = [endpoint]
    if user_id:
        key_parts.append(f"user:{user_id}")
    
    for key, value in sorted(params.items()):
        if value is not None:
            key_parts.append(f"{key}:{value}")
    
    return ":".join(key_parts)

# =============================================================================
# RATE LIMITING DEPENDENCIES
# =============================================================================

def rate_limit(
    max_requests: int = 100,
    window_minutes: int = 60
):
    """
    Dependencia para rate limiting
    """
    def rate_limiter(
        request_ip: str = Header(..., alias="X-Real-IP"),
        redis_client: redis.Redis = Depends(get_redis)
    ):
        key = f"rate_limit:{request_ip}"
        current = redis_client.get(key)
        
        if current is None:
            # Primera request en la ventana de tiempo
            redis_client.setex(key, window_minutes * 60, 1)
            return True
        
        current_count = int(current)
        if current_count >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit excedido. Máximo {max_requests} requests por {window_minutes} minutos"
            )
        
        redis_client.incr(key)
        return True
    
    return rate_limiter

# =============================================================================
# BUSINESS LOGIC DEPENDENCIES
# =============================================================================

def validate_product_ownership(
    product_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Validar que el usuario actual sea dueño del producto
    """
    from app.models.product import Product
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Producto no encontrado"
        )
    
    # Si no es admin y no es el dueño
    if not current_user.is_admin and product.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a este producto"
        )
    
    return product

def validate_business_hours():
    """
    Validar que la API esté siendo usada en horarios de negocio
    """
    current_hour = datetime.now().hour
    if current_hour < 6 or current_hour > 22:  # 6 AM - 10 PM
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API disponible solo en horarios de negocio (6 AM - 10 PM)"
        )
    return True

# =============================================================================
# LOGGING DEPENDENCIES
# =============================================================================

def log_request(
    request_id: str = Header(None, alias="X-Request-ID"),
    user_agent: str = Header(None, alias="User-Agent")
) -> dict:
    """
    Dependencia para logging de requests
    """
    import uuid
    
    if not request_id:
        request_id = str(uuid.uuid4())
    
    logger.info(f"Request {request_id} - User-Agent: {user_agent}")
    
    return {
        "request_id": request_id,
        "user_agent": user_agent
    }

# =============================================================================
# FILE UPLOAD DEPENDENCIES
# =============================================================================

def validate_file_upload(
    max_size_mb: int = 5,
    allowed_types: list = None
):
    """
    Dependencia para validar uploads de archivos
    """
    if allowed_types is None:
        allowed_types = ["image/jpeg", "image/png", "image/gif"]
    
    def file_validator(file):
        if file.size > max_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Archivo muy grande. Máximo {max_size_mb}MB"
            )
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Tipo de archivo no permitido. Usar: {', '.join(allowed_types)}"
            )
        
        return file
    
    return file_validator

# =============================================================================
# EJEMPLOS DE USO EN ENDPOINTS
# =============================================================================

"""
Ejemplos de cómo usar estas dependencias en endpoints:

# Endpoint básico con BD
@router.get("/products/")
def get_products(db: DatabaseSession):
    return db.query(Product).all()

# Endpoint con autenticación
@router.post("/products/")
def create_product(
    product_data: ProductCreate,
    current_user: ActiveUser,
    db: DatabaseSession
):
    # El usuario ya está validado y activo
    pass

# Endpoint solo para admins
@router.delete("/products/{product_id}")
def delete_product(
    product_id: int,
    admin_user: AdminUser,
    db: DatabaseSession
):
    # Solo usuarios admin pueden acceder
    pass

# Endpoint con paginación
@router.get("/products/")
def get_products(
    pagination: dict = Depends(validate_pagination),
    db: DatabaseSession
):
    skip = pagination["skip"]
    limit = pagination["limit"]
    pass

# Endpoint con rate limiting
@router.post("/upload/")
def upload_file(
    file: UploadFile,
    _: bool = Depends(rate_limit(max_requests=10, window_minutes=1)),
    validate_file = Depends(validate_file_upload(max_size_mb=2))
):
    validated_file = validate_file(file)
    pass

# Endpoint con validación de propiedad
@router.get("/products/{product_id}")
def get_my_product(
    product = Depends(validate_product_ownership)
):
    # El producto ya está validado y el usuario tiene permisos
    return product
"""