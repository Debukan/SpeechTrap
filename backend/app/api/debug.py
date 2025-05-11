from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
import logging
from app.db.deps import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from sqlmodel import select

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/routes")
async def list_routes(request: Request):
    """Отображает список всех маршрутов API"""
    routes = []
    for route in request.app.routes:
        routes.append(
            {
                "path": route.path,
                "name": route.name,
                "methods": getattr(route, "methods", None),
            }
        )
    return {"routes": routes}


@router.get("/users")
async def list_users(db: Session = Depends(get_db)):
    """Отображает список всех пользователей (только для отладки)"""
    try:
        statement = select(User)
        results = db.execute(statement).all()
        users = [row[0] for row in results]

        return {
            "users": [
                {"id": user.id, "name": user.name, "email": user.email}
                for user in users
            ]
        }
    except Exception as e:
        logger.exception("Error listing users")
        return {"error": str(e)}


@router.post("/create-user")
async def create_test_user(
    name: str, email: str, password: str, db: Session = Depends(get_db)
):
    """Создает тестового пользователя (только для отладки)"""
    try:
        user = User(name=name, email=email)
        user.set_password(password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"status": "success", "user_id": user.id}
    except Exception as e:
        logger.exception("Error creating test user")
        db.rollback()
        return {"status": "error", "message": str(e)}
