from fastapi import APIRouter, Response

from app.api.attach import get_attach

router = APIRouter(prefix="/attachs")


@router.get("/{id}")
def api_get_attachs(id: str):
    return Response(content=get_attach(id), media_type="image/png")
