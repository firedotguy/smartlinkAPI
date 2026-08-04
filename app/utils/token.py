from random import choice
from string import ascii_letters, digits


def gen_token(length: int = 50):
    return "".join([choice(ascii_letters + digits) for _ in range(length)])


def mask_token(token: str):
    if len(token) > 10:
        return token[:7] + "***" + token[-7:]
    return "*" * len(token)
