from __future__ import annotations

from dataclasses import dataclass

from pi_egt.network.weather import WeatherData, THUNDERSTORM_CODES
from pi_egt import config


@dataclass
class LightningRisk:
    level: str              # 'low' | 'moderate' | 'high' | 'active'
    cape: float             # J/kg from nearest forecast hour
    lightning_potential: float  # 0–100 %
    thunderstorm_active: bool
    description: str


_LEVEL_ORDER = ('low', 'moderate', 'high', 'active')


def assess_risk(weather: WeatherData) -> LightningRisk:
    """
    Derive lightning risk from Open-Meteo CAPE and weather codes.
    'active' means a thunderstorm weather code is forecast for the current hour.
    """
    if not weather.hourly:
        return LightningRisk('low', 0.0, 0.0, False, 'No forecast data')

    fc = weather.hourly[0]
    cape = fc.cape
    lp = fc.lightning_potential
    ts_active = fc.weather_code in THUNDERSTORM_CODES

    if ts_active:
        level, desc = 'active', 'Thunderstorm active now'
    elif cape >= config.CAPE_HIGH or lp >= config.LIGHTNING_POTENTIAL_HIGH:
        level = 'high'
        desc = f'High storm risk (CAPE {cape:.0f} J/kg)'
    elif cape >= config.CAPE_MODERATE or lp >= config.LIGHTNING_POTENTIAL_MODERATE:
        level = 'moderate'
        desc = f'Moderate storm risk (CAPE {cape:.0f} J/kg)'
    else:
        level = 'low'
        desc = 'Low storm risk'

    return LightningRisk(level, cape, lp, ts_active, desc)
