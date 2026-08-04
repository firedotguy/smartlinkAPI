def format_mac(value: str | None) -> str | None:
    if value is None:
        return
    return ":".join(value.replace("-", "")[i : i + 2] for i in range(0, len(value.replace("-", "")), 2))
