from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import User
from app.routes import router
from app.security import hash_password
from app.web import render


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    if not settings.SEED_ADMIN:
        return
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            return
        db.add(
            User(
                name=settings.ADMIN_NAME,
                phone=settings.ADMIN_PHONE,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
            )
        )
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=settings.SESSION_HTTPS_ONLY,
    same_site="lax",
    max_age=8 * 60 * 60,
)
app.mount("/static", StaticFiles(directory=Path(__file__).resolve().parent / "static"), name="static")
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 303 and exc.headers and exc.headers.get("Location"):
        from app.web import redirect

        return redirect(exc.headers["Location"])
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return render(request, "error.html", status_code=exc.status_code, message=str(exc.detail))

