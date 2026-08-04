from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.snmp import get_ont
from app.utils import storage

router = APIRouter(prefix="/onts")


@router.get("/{sn}")
def api_get_ont(sn: str, olt_id: int):
    olt = storage.olts.get(olt_id)
    if olt is None:
        return JSONResponse({"detail": "olt not found"}, 404)

    ont = get_ont(olt, sn)
    if ont is None:
        return JSONResponse({"detail": "ont not found"}, 404)
    return {"olt": olt.model_dump(exclude={"snmp_community", "snmp_protocol", "ip"}), "ont": ont}
