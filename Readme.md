# TaskMaster API

API y frontend ligero para gestionar notas/tareas con autenticación JWT. Incluye CI y CD a Azure Container Apps, y soporte de base de datos local (SQLite) o gestionada (Neon/PostgreSQL).

Stack principal: FastAPI, SQLAlchemy, Pydantic, Uvicorn, Psycopg (PostgreSQL), HTML/CSS/JS vanilla, Pytest, Docker, GitHub Actions.

Estado de CI/CD: pruebas y despliegue automático en cada push a `main` (si están configurados los secretos de Azure).

## Características

- Autenticación JWT (Authorization: Bearer) con expiración configurable.
- CRUD de tareas scoped al usuario; validaciones de título; soporte de descripción.
- Listado con paginación (`page`, `limit`) y búsqueda por título (`q`).
- Frontend multipágina: `login.html`, `register.html`, `notes.html` (toasts, modal, loading states, búsqueda con debounce).
- Esquema de BD auto-creado en arranque (migraciones aditivas simples, p. ej. columna `description`).
- Pool de conexiones con `pool_pre_ping` para bases serverless (Neon) y reconexión limpia.
- Dockerfile listo (puerto 8000). Sin `DATABASE_URL` por defecto → usa SQLite.
- CI (pytest) y CD a Azure Container Apps (imagen construida en ACR y update de la app).

## Estructura del proyecto

```text
app/
  main.py           # Entrada FastAPI; monta frontend estático
  config.py         # Config desde variables de entorno (fallbacks seguros)
  database.py       # SQLAlchemy engine/session (pool_pre_ping habilitado)
  models/           # Modelos ORM (User, Task)
  routers/          # Rutas /auth y /tasks
  schemas/          # Esquemas Pydantic
  utils/            # Utilidades (JWT, hash)
  frontend/         # HTML/JS/CSS del cliente
tests/              # Pruebas (pytest)
.github/workflows/
  ci.yml            # CI: pruebas (local y con servicio PostgreSQL)
  deploy-aca.yml    # CD: build en ACR y despliegue a Azure Container Apps
Dockerfile          # Imagen de la API (expuesto 8000)
```

## Configuración (variables de entorno)

- `SECRET_KEY` (recomendado definir en todos los entornos)
- `ALGORITHM` (por defecto `HS256`)
- `ACCESS_TOKEN_EXPIRE_MINUTES` (por defecto `60`)
- `DATABASE_URL`
  - Si está vacío/no definido: usa SQLite `sqlite:///./taskmaster.db`.
  - PostgreSQL (psycopg3): `postgresql+psycopg://USER:PASS@HOST:5432/DB?sslmode=require`.
  - Neon (recomendado para aprendizaje): añade `?sslmode=require&channel_binding=require`.

Ejemplos:

```bash
# SQLite (local)
DATABASE_URL=sqlite:///./taskmaster.db

# Neon / PostgreSQL gestionado
DATABASE_URL=postgresql+psycopg://user:pass@host/db?sslmode=require&channel_binding=require
```

## Ejecutar localmente

Requisitos: Python 3.11 recomendado (alineado con CI), pip.

```bash
python -m venv .venv
source .venv/bin/activate         # Windows: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requeriments.txt

# Opción A: SQLite (sin definir DATABASE_URL)
uvicorn app.main:app --reload

# Opción B: Neon (misma que producción)
export DATABASE_URL="postgresql+psycopg://user:pass@host/db?sslmode=require&channel_binding=require"
uvicorn app.main:app --reload
```

Frontend:
- `http://127.0.0.1:8000/` (sirve `app/frontend`)
- Swagger: `http://127.0.0.1:8000/docs`

## Pruebas

```bash
pytest -q
```

El CI también ejecuta un job con servicio PostgreSQL (Docker) para mayor cobertura.

## Docker

Construir y ejecutar localmente:

```bash
docker build -t taskmaster-api:local .
docker run --rm -p 8000:8000 taskmaster-api:local
```

Notas:
- El Dockerfile no fuerza `DATABASE_URL`. Sin definirla, la app usa SQLite.
- Para usar Postgres, pasa `-e DATABASE_URL=postgresql+psycopg://...` al `docker run`.

## API (resumen)

- POST `/auth/register` { email, password } → 201
- POST `/auth/login` { email, password } → { access_token, token_type }
- GET `/tasks/` [Bearer] soporta `page`, `limit`, `q` (búsqueda por título)
- POST `/tasks/` { title, description? } [Bearer]
- DELETE `/tasks/{id}` [Bearer]

Errores comunes: 401 (token inválido/expirado), 422 (datos inválidos).

## Despliegue a Azure Container Apps (resumen)

Dos rutas soportadas:

1) CLI (rápido y reproducible)
- Crear RG, ACR (con admin user), Log Analytics, ACA Environment.
- Construir imagen en ACR: `az acr build -r <acr> -g <rg> -t taskmaster-api:latest .`
- Crear/actualizar Container App con ingress 8000.
- Establecer variables (SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES, DATABASE_URL [Neon]).
- Obtener FQDN y revisar logs.

2) GitHub Actions (automático en cada push a `main`)
- Workflow: `.github/workflows/deploy-aca.yml`.
- Secretos requeridos:
  - `AZURE_CREDENTIALS` (json sdk-auth del Service Principal con rol Contributor en el RG y rol AcrPush en el ACR)
  - `AZURE_RESOURCE_GROUP` (ej. `tm-rg`)
  - `ACR_NAME` (ej. `tmregistry12345`)
  - `AZURE_CONTAINERAPP_NAME` (ej. `taskmaster-api`)
- El job de despliegue:
  - Ejecuta tests.
  - Construye imagen en ACR usando `az acr build` (tag SHA del commit).
  - `az containerapp update` para apuntar a la nueva imagen.
  - Imprime el FQDN.

Requisitos previos (una sola vez por suscripción):
- Registrar providers: `Microsoft.App`, `Microsoft.OperationalInsights`.
- Asignar `AcrPush` al Service Principal sobre el ACR.
- En la Container App, configurar credenciales de registro (`az containerapp registry set ...`).

## Troubleshooting

- 400 Invalid URL en `az containerapp update`:
  - Suele ser por caracteres ocultos (\r) en secretos. Sanea variables o vuelve a guardarlas sin saltos.
- AuthorizationFailed al registrar providers:
  - El SP solo tiene permisos a nivel RG. Registra providers con tu usuario Owner/Contributor a nivel suscripción.
- `ModuleNotFoundError: psycopg` en local:
  - Usa Python 3.11 y `pip install -r requeriments.txt`. O elimina `DATABASE_URL` para trabajar con SQLite.
- Pérdida de datos tras reinicio en ACA:
  - Estabas en SQLite (FS efímero). Usa Neon/Postgres, o monta Azure Files para persistir SQLite.

## Seguridad

- No subas `azure-credentials.json` al repo (está en `.gitignore`). Usa GitHub Secrets.
- Rota credenciales si se compartieron públicamente y actualiza variables/secretos.

## Licencia

MIT
