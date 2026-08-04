from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.snmp import get_ont
from app.ssh import restart, toggle_catv
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
    return {"olt": olt.model_dump(exclude={"snmp_community", "snmp_protocol", "ip"}), **ont}


@router.post("/{sn}/restart", status_code=204)
def api_post_ont_restart(sn: str, olt_id: int):
    olt = storage.olts.get(olt_id)
    if olt is None:
        return JSONResponse({"detail": "olt not found"}, 404)

    res = restart(olt.ip, sn)
    if res:
        return JSONResponse({"detail": res["detail"]}, res["code"])


@router.patch("/{sn}/catv/{catv_id}", status_code=204)
def api_post_toggle_catv(sn: str, olt_id: int, catv_id: int, state: bool):
    olt = storage.olts.get(olt_id)
    if olt is None:
        return JSONResponse({"detail": "olt not found"}, 404)

    res = toggle_catv(olt.ip, sn, catv_id, state)
    if res:
        return JSONResponse({"detail": res["detail"]}, res["code"])
