"""Plane-of-array irradiance transposition."""

from __future__ import annotations

import math

from energy_core.solar_intelligence.geometry import SolarGeometryService


class PoaTranspositionService:
    """GHI/DNI/DHI → POA using isotropic + Hay-Davies hybrid."""

    def __init__(self, geometry: SolarGeometryService) -> None:
        self._geometry = geometry

    def poa_irradiance(
        self,
        *,
        ts,
        ghi_wm2: float,
        dni_wm2: float | None,
        dhi_wm2: float | None,
        tilt_deg: float,
        azimuth_deg: float,
        albedo: float = 0.2,
    ) -> float:
        if ghi_wm2 <= 0:
            return 0.0

        elev, sun_az = self._geometry.elevation_azimuth(ts)
        if elev <= 0:
            return 0.0

        dhi = dhi_wm2 if dhi_wm2 is not None else max(0.0, ghi_wm2 * 0.3)
        dni = dni_wm2
        if dni is None:
            cos_elev = max(math.sin(math.radians(elev)), 0.01)
            beam_horizontal = max(0.0, ghi_wm2 - dhi)
            dni = beam_horizontal / cos_elev if cos_elev > 0 else 0.0

        tilt_rad = math.radians(tilt_deg)
        elev_rad = math.radians(elev)
        sun_az_rad = math.radians(sun_az)
        surf_az_rad = math.radians(azimuth_deg)

        cos_theta = (
            math.sin(elev_rad) * math.cos(tilt_rad)
            + math.cos(elev_rad) * math.sin(tilt_rad) * math.cos(sun_az_rad - surf_az_rad)
        )
        cos_theta = max(0.0, cos_theta)

        beam_poa = dni * cos_theta

        # Hay-Davies anisotropic diffuse fraction
        cos_elev = max(math.sin(elev_rad), 0.01)
        airm = ghi_wm2 / (1361.0 * cos_elev) if cos_elev > 0 else 0.0
        aniso = min(1.0, max(0.0, airm))
        dhi_iso = dhi * (1.0 - aniso)
        dhi_circ = dhi * aniso * cos_theta / cos_elev if cos_elev > 0 else 0.0
        diffuse_poa = dhi_iso * (1.0 + math.cos(tilt_rad)) / 2.0 + dhi_circ

        ground_reflected = ghi_wm2 * albedo * (1.0 - math.cos(tilt_rad)) / 2.0
        return max(0.0, beam_poa + diffuse_poa + ground_reflected)
