"""Synthetic identifier generation.

Every identifier produced here is fabricated. Aadhaar numbers carry a valid
Verhoeff checksum and card numbers a valid Luhn checksum so that the
deterministic Fast Lane detectors are exercised realistically -- but they are
generated from a fixed seed and correspond to no real person.
"""
from __future__ import annotations

import random
import string

_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6], [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8], [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2], [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4], [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2], [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0], [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5], [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]
_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def verhoeff_check(number: str) -> bool:
    c = 0
    for i, ch in enumerate(reversed(number)):
        if not ch.isdigit():
            return False
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def verhoeff_checksum(number: str) -> str:
    c = 0
    for i, ch in enumerate(reversed(number)):
        c = _D[c][_P[(i + 1) % 8][int(ch)]]
    return str(_INV[c])


def luhn_check(number: str) -> bool:
    digits = [int(d) for d in number if d.isdigit()]
    if len(digits) < 12:
        return False
    total, parity = 0, len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def make_aadhaar(rng: random.Random) -> str:
    body = str(rng.randint(2, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(10))
    full = body + verhoeff_checksum(body)
    return f"{full[:4]} {full[4:8]} {full[8:]}"


def make_pan(rng: random.Random) -> str:
    a = "".join(rng.choice(string.ascii_uppercase) for _ in range(5))
    n = "".join(str(rng.randint(0, 9)) for _ in range(4))
    return f"{a}{n}{rng.choice(string.ascii_uppercase)}"


def make_card(rng: random.Random) -> str:
    body = "4" + "".join(str(rng.randint(0, 9)) for _ in range(14))
    for d in "0123456789":
        if luhn_check(body + d):
            full = body + d
            return f"{full[:4]} {full[4:8]} {full[8:12]} {full[12:]}"
    return "4111 1111 1111 1111"


def make_phone(rng: random.Random) -> str:
    return f"+91 {rng.randint(70000, 99999)} {rng.randint(10000, 99999)}"


def make_email(name: str) -> str:
    slug = name.lower().replace(" ", ".")
    return f"{slug}@example.com"
