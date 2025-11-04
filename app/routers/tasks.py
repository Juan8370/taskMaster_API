from fastapi import APIRouter, Depends, HTTPException, Header, Query
from datetime import datetime, UTC
from jose import jwt, JWTError, ExpiredSignatureError
from sqlalchemy.orm import Session
from typing import Optional
from sqlalchemy import inspect
from app.schemas.task import TaskCreate, TaskOut
from app.models.task import Task
from app.database import get_db
from app.config import SECRET_KEY, ALGORITHM

from math import ceil

router = APIRouter(prefix="/tasks", tags=["tasks"])

def _extract_token(authorization: Optional[str], token_query: Optional[str]) -> Optional[str]:
    """Return token from Authorization header (Bearer ...) or token query param (compat).
    Header has precedence.
    """
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    return token_query


def get_current_user(authorization: Optional[str] = Header(None), token: Optional[str] = None):
    tok = _extract_token(authorization, token)
    if not tok:
        # If token is omitted entirely, return 422 to keep parity with previous
        # FastAPI validation behavior for missing required params in tests.
        raise HTTPException(status_code=422, detail="Missing token")
    try:
        # jwt.decode validates exp automatically
        payload = jwt.decode(tok, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token: missing user")
        return email
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/", response_model=TaskOut)
def create_task(task: TaskCreate, db: Session = Depends(get_db), authorization: Optional[str] = Header(None), token: Optional[str] = None):
    user = get_current_user(authorization, token)
    new = Task(title=task.title, description=(task.description or ""), user_email=user)
    db.add(new)
    db.commit()
    db.refresh(new)
    return new

@router.get("/")
def list_tasks(q: Optional[str] = Query(None, description="Search by title"), page: Optional[int] = None, limit: Optional[int] = None, db: Session = Depends(get_db), authorization: Optional[str] = Header(None), token: Optional[str] = None):
    """If page and limit are provided, return paginated result dict {items,page,limit,total,pages}.
    Otherwise return plain list for backward compatibility.
    """
    user = get_current_user(authorization, token)
    query = db.query(Task).filter(Task.user_email == user)
    if q:
        query = query.filter(Task.title.ilike(f"%{q}%"))
    total = query.count()
    if page is None or limit is None:
        return query.all()

    # normalize page/limit
    if page < 1:
        page = 1
    if limit < 1:
        limit = 10
    pages = ceil(total / limit) if total > 0 else 1
    items = query.limit(limit).offset((page - 1) * limit).all()
    return {"items": items, "page": page, "limit": limit, "total": total, "pages": pages}


@router.delete("/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), authorization: Optional[str] = Header(None), token: Optional[str] = None):
    user = get_current_user(authorization, token)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_email != user:
        raise HTTPException(status_code=403, detail="Not allowed to delete this task")
    db.delete(task)
    db.commit()
    return {"detail": "deleted"}
