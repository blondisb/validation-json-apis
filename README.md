# Clonar y setup
cd product-api
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt

# Con Docker
docker-compose up --build

# Ejecutar directamente
uvicorn app.main:app --reload

# Ejecutar tests
pytest

# Generar migración
alembic revision --autogenerate -m "Create product table"

# Aplicar migraciones
alembic upgrade head



La documentación interactiva estará disponible en: http://localhost:8000/docs