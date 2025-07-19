from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.exceptions import add_exception_handlers
from app.core.middleware import add_middleware
from app.core.logging import setup_logging
from app.api.v1.api import api_router
from app.config.settings import settings

# Configurar logging
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API para gestión de productos con validación rigurosa",
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Configurar middleware
add_middleware(app)

# Configurar manejadores de excepciones
add_exception_handlers(app)

# Incluir routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {"message": f"Bienvenido a {settings.PROJECT_NAME}"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}