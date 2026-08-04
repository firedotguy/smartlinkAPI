from json import load

from fastapi import APIRouter

from app import __version__

router = APIRouter(prefix="/platform")


@router.get("")
def api_get_platform():
    data = load(open("platform.json", "r"))
    data["version"] = __version__
    return data
