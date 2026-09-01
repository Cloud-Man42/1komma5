"""Simple geohash for lookup cache keys (~6 char precision)."""

from __future__ import annotations

_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def encode(lat: float, lon: float, precision: int = 6) -> str:
    lat_range = (-90.0, 90.0)
    lon_range = (-180.0, 180.0)
    bits = [16, 8, 4, 2, 1]
    geohash: list[str] = []
    bit = 0
    ch = 0
    even = True
    while len(geohash) < precision:
        if even:
            mid = (lon_range[0] + lon_range[1]) / 2
            if lon >= mid:
                ch |= bits[bit]
                lon_range = (mid, lon_range[1])
            else:
                lon_range = (lon_range[0], mid)
        else:
            mid = (lat_range[0] + lat_range[1]) / 2
            if lat >= mid:
                ch |= bits[bit]
                lat_range = (mid, lat_range[1])
            else:
                lat_range = (lat_range[0], mid)
        even = not even
        if bit < 4:
            bit += 1
        else:
            geohash.append(_BASE32[ch])
            bit = 0
            ch = 0
    return "".join(geohash)


def bounds_key(lat: float, lon: float, radius_m: float, *, precision: int = 6) -> str:
    """Build ChargeFinder map bounds key: NE geohash - SW geohash."""
    import math

    dlat = radius_m / 111_320.0
    dlon = radius_m / (111_320.0 * max(math.cos(math.radians(lat)), 0.01))
    ne = encode(lat + dlat, lon + dlon, precision)
    sw = encode(lat - dlat, lon - dlon, precision)
    return f"{ne}-{sw}"
