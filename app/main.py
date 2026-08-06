from contextlib import asynccontextmanager
from time import time
from typing import Callable

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from uvicorn import run

from app.api.device import get_olts
from app.api.inventory import get_item_categories
from app.api.tariff import get_tariffs
from app.config import HOST, LOG_COLORFUL, LOG_LEVEL, PORT, UPDATE_ONT_INDEXES_ON_STARTUP
from app.db import Session, create_db, get_db
from app.db.crud import check_token
from app.routers import router
from app.snmp import update_ont_indexes
from app.utils import storage
from app.utils.logger import format_request, get_logger, setup_logging

setup_logging(LOG_LEVEL, LOG_COLORFUL)
l = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    l.info("server start")
    create_db()

    # app.state.provinces = get_provinces()
    storage.tariffs = get_tariffs()
    storage.item_categories = get_item_categories()
    storage.olts = get_olts()
    if UPDATE_ONT_INDEXES_ON_STARTUP:
        update_ont_indexes()

    try:
        yield
    finally:
        l.info("server stop")


def verify_token(request: Request, db: Session = Depends(get_db)):
    if request.url.path.rsplit("/", maxsplit=1)[-1] not in ("login", "platform"):
        if not request.cookies.get("token") or (request.cookies.get("token") and not check_token(db, request.cookies["token"])):
            l.debug("unauthorized call %s", request.url.path)
            raise HTTPException(detail="unauthorized", status_code=401)


app = FastAPI(title="SmartLinkAPI", lifespan=lifespan, dependencies=[Depends(verify_token)], redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://{HOST}:{PORT}", "https://smartlink.neotelecom.kg", "http://146.120.230.7"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.middleware("http")
async def middleware(request: Request, call_next: Callable) -> Response:
    start = time()
    response: Response = await call_next(request)
    # custom access log
    l.info(format_request(request, response, round(time() - start, 2), LOG_COLORFUL), extra={"highlighter": None})
    return response


app.include_router(router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    """Get favicon"""
    return FileResponse("favicon.ico")


run(app, host=HOST, port=PORT, log_level="warning")
