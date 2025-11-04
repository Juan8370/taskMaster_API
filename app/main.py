from fastapi import FastAPI
import fastapi
from fastapi.staticfiles import StaticFiles
from app.database import Base, engine
from sqlalchemy import inspect, text
from app.routers import auth, tasks

Base.metadata.create_all(bind=engine)

# Ensure new columns exist without Alembic (simple additive migrations)
def _ensure_schema():
	try:
		insp = inspect(engine)
		cols = [c['name'] for c in insp.get_columns('tasks')]
		if 'description' not in cols:
			with engine.begin() as conn:
				conn.execute(text('ALTER TABLE tasks ADD COLUMN description TEXT'))
	except Exception:
		# best-effort; ignore errors to not block startup
		pass

_ensure_schema()

app = FastAPI(title="TaskMaster MVP")

# API routers
app.include_router(auth.router)
app.include_router(tasks.router)

# Serve a minimal frontend SPA from / (index.html in app/frontend)
app.mount("/", StaticFiles(directory="app/frontend", html=True), name="frontend")

# Generic error handler to return JSON errors for unexpected exceptions
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
	# Keep HTTPException behavior
	from fastapi import HTTPException
	if isinstance(exc, HTTPException):
		raise exc
	return fastapi.responses.JSONResponse(status_code=500, content={"detail": "Internal server error"})
