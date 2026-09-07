from ezsnmp import Session
from ezsnmp.exceptions import TimeoutError

from app.db import get_db
from app.db.crud import get_ont as get_ont_index
from app.db.crud import set_ont
from app.db.models import Ont
from app.enums import EthDuplexMode, OntLastDownCause
from app.models.item import Olt
from app.utils import storage
from app.utils.logger import get_logger
from app.utils.snmp import check_none, convert_status, decode_datetime, decode_sn, get_eth_speed, normalize_sn

l = get_logger("snmp")


def get_session(olt: Olt) -> Session | None:
    l.debug("connect to olt %s community=%s", olt.ip, olt.snmp_community)
    return Session(olt.ip, version=olt.snmp_protocol, community=olt.snmp_community, timeout=20, retries=3)


def update_ont_indexes():
    l.info("update ont indexes")
    db = next(get_db())

    for olt in storage.olts.values():
        session = get_session(olt)
        if not session:
            continue

        try:
            onts = session.bulk_walk("1.3.6.1.4.1.2011.6.128.1.1.2.43.1.3")
        except TimeoutError:
            l.error("timeout connecting to olt ip=%s", olt.ip)
            continue
        finally:
            session.close()

        for sn in onts:
            try:
                set_ont(db, decode_sn(sn.value), sn.oid.split(".")[-1], sn.index)
            except ValueError as e:
                l.warning("skip invalid ont olt=%s sn=%r: %s", olt.ip, sn.value, e)

        db.commit()


def _get(session: Session, name: str, ont: Ont, port_id: int | None = None, *, add_ont_id: bool = True, default: bool | int | None = None):
    oids = {
        "temp_olt": "23.1.1",
        "tx_olt": "23.1.4",
        "model": "45.1.4",
        "software_version": "45.1.5",
        "status": "46.1.15",
        "status_config": "46.1.16",
        "status_discovery": "46.1.17",
        "status_match": "46.1.18",
        "status_dba": "46.1.19",
        "status_isolation": "46.1.26",
        "status_battery": "46.1.27",
        "distance": "46.1.20",
        "last_up": "46.1.22",
        "last_down": "46.1.23",
        "last_down_cause": "46.1.24",
        "last_dying_gasp": "46.1.25",
        "mgtm_count": "47.1.1",
        "eth_count": "47.1.2",
        "pots_count": "47.1.3",
        "catv_count": "47.1.9",
        "ip": "49.1.2",
        "mac": "49.1.4",
        "temp": "51.1.1",
        "bias": "51.1.2",
        "tx": "51.1.3",
        "rx": "51.1.4",
        "voltage": "51.1.5",
        "rx_olt": "51.1.6",
        "rx_catv": "51.1.7",
        "eth_duplex": "62.1.3",
        "eth_speed": "62.1.4",
        "eth_status": "62.1.5",
        "eth_actual_status": "62.1.22",
        "catv_status": "63.1.2",
        "catv_actual_status": "63.1.3"
    }

    oid = f"{oids[name]}.{ont.ifindex}{'.' + str(ont.ont_id) if add_ont_id else ''}{'.' + str(port_id) if port_id is not None else ''}"

    l.debug("> %s %s", name, oid)
    res = session.get(f"1.3.6.1.4.1.2011.6.128.1.1.2.{oid}")[0].value
    l.debug("< %s", res)

    if res in ("2147483647", "No Such Instance currently exists at this OID", "00 00 00 00 00 00 00 00 00 00 00", "0.0.0.0", "-1"):
        return default if default is not None else None

    elif res.lstrip("-").isdigit():
        return int(res)
    return res


def get_ont(olt: Olt, sn: str) -> dict | None:
    sn = normalize_sn(sn)
    l.info("get ont sn=%s olt=%s", sn, olt.id)
    ont = get_ont_index(next(get_db()), sn)
    if ont is None:
        return

    session = get_session(olt)
    assert session

    mac = _get(session, "mac", ont, 0)
    if mac:
        mac = ":".join(mac.split(" ")).lower()
    else:
        mac = None

    return {
        "id": ont.ont_id,
        "ifindex": ont.ifindex,
        "temp": _get(session, "temp", ont),
        # "temp_olt": _get(session, "temp_olt", ont), # always none
        "online": convert_status(_get(session, "status", ont)),  # {
        # "run": convert_status(_get(session, "status", ont)),
        # "config": OntConfigStatus(_get(session, "status_config", ont)),
        # "discovery": convert_status(_get(session, "status_discovery", ont)),
        # "match": OntMatchStatus(_get(session, "status_match", ont)),
        # "dba": convert_status(_get(session, "status_dba", ont)),
        # "isolation": bool(_get(session, "status_isolation", ont)),
        # "battery": OntBatteryStatus(_get(session, "status_battery", ont))
        # },
        "last_up": decode_datetime(_get(session, "last_up", ont)),
        "last_down": decode_datetime(_get(session, "last_down", ont)),
        "last_down_cause": OntLastDownCause(_get(session, "last_down_cause", ont)).name,
        "distance": check_none(_get(session, "distance", ont)),
        # "last_dying_gasp": decode_datetime(_get(session, "last_dying_gasp", ont)),
        "eth": [
            {
                "id": i,
                "duplex": EthDuplexMode(_get(session, "eth_duplex", ont, i)).name,
                "speed": get_eth_speed(_get(session, "eth_speed", ont, i)),
                "status": convert_status(_get(session, "eth_status", ont, i, default=False)),
                "actual_status": convert_status(_get(session, "eth_actual_status", ont, i, default=False))
            }
            for i in range(1, _get(session, "eth_count", ont, default=0) + 1)
        ],
        "catv": [
            {
                "id": i,
                "status": convert_status(_get(session, "catv_status", ont, i, default=False)),
                "actual_status": convert_status(_get(session, "catv_actual_status", ont, i, default=False))
            }
            for i in range(1, _get(session, "catv_count", ont) + 1)
        ],
        "model": check_none(_get(session, "model", ont)),
        "tx": check_none(_get(session, "tx", ont, default=0) / 100),
        "rx": check_none(_get(session, "rx", ont, default=0) / 100),
        "tx_olt": check_none(_get(session, "tx_olt", ont, add_ont_id=False, default=0) / 100),
        "rx_olt": check_none((_get(session, "rx_olt", ont, default=10000) - 10000) / 100),
        # "rx_catv": _get(session, "rx_catv", ont, default=0) / 100,
        "ip": _get(session, "ip", ont, 0),
        "mac": mac
    }
