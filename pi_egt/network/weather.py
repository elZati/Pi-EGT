from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import requests

GEOCODING_URL = 'https://geocoding-api.open-meteo.com/v1/search'
FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'

WMO_DESCRIPTIONS: dict[int, str] = {
    0: 'Clear sky',
    1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
    45: 'Fog', 48: 'Icy fog',
    51: 'Light drizzle', 53: 'Drizzle', 55: 'Dense drizzle',
    61: 'Slight rain', 63: 'Rain', 65: 'Heavy rain',
    71: 'Slight snow', 73: 'Snow', 75: 'Heavy snow',
    77: 'Snow grains',
    80: 'Rain showers', 81: 'Showers', 82: 'Heavy showers',
    85: 'Snow showers', 86: 'Heavy snow showers',
    95: 'Thunderstorm', 96: 'Thunderstorm + hail', 99: 'Thunderstorm + heavy hail',
}

WMO_ICONS: dict[int, str] = {
    0: '☀',
    1: '\U0001f324', 2: '⛅', 3: '☁',
    45: '\U0001f32b', 48: '\U0001f32b',
    51: '\U0001f326', 53: '\U0001f326', 55: '\U0001f327',
    61: '\U0001f327', 63: '\U0001f327', 65: '\U0001f327',
    71: '❄', 73: '❄', 75: '❄', 77: '❄',
    80: '\U0001f326', 81: '\U0001f326', 82: '⛈',
    85: '\U0001f328', 86: '\U0001f328',
    95: '⛈', 96: '⛈', 99: '⛈',
}

THUNDERSTORM_CODES = {95, 96, 99}


@dataclass
class DailyForecast:
    temp_min: float
    temp_max: float
    weather_code: int


@dataclass
class HourlyForecast:
    """Used only for lightning risk assessment (CAPE / lightning_potential)."""
    time: datetime
    weather_code: int
    cape: float
    lightning_potential: float


@dataclass
class WeatherData:
    location_name: str
    current_temp: float
    current_code: int
    today: DailyForecast | None = None
    hourly: list[HourlyForecast] = field(default_factory=list)


def search_location(name: str) -> list[dict]:
    resp = requests.get(
        GEOCODING_URL,
        params={'name': name, 'count': 5, 'language': 'en', 'format': 'json'},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get('results', [])


def fetch_forecast(lat: float, lon: float, location_name: str) -> WeatherData:
    resp = requests.get(
        FORECAST_URL,
        params={
            'latitude': lat,
            'longitude': lon,
            'current': 'temperature_2m,weather_code',
            'daily': 'temperature_2m_max,temperature_2m_min,weather_code',
            'hourly': 'weather_code,cape,lightning_potential',
            'timezone': 'auto',
            'forecast_days': 1,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    utc_offset_s = data.get('utc_offset_seconds', 0)
    tz = timezone(timedelta(seconds=utc_offset_s))

    def _parse(t: str) -> datetime:
        return datetime.fromisoformat(t).replace(tzinfo=tz)

    # Current conditions
    current = data['current']

    # Today's daily summary (index 0 = today)
    daily = data.get('daily', {})
    today: DailyForecast | None = None
    if daily.get('temperature_2m_max'):
        today = DailyForecast(
            temp_min=float(daily['temperature_2m_min'][0] or 0.0),
            temp_max=float(daily['temperature_2m_max'][0] or 0.0),
            weather_code=int(daily['weather_code'][0] or 0),
        )

    # Hourly (for lightning risk only — next 6 hours)
    hourly = data.get('hourly', {})
    lp_list: list[float] = hourly.get('lightning_potential') or []
    now = datetime.now(timezone.utc).astimezone(tz)
    forecasts: list[HourlyForecast] = []
    for i, t_str in enumerate(hourly.get('time', [])):
        t = _parse(t_str)
        if t < now:
            continue
        cape_val = (hourly.get('cape') or [None])[i]
        lp_val = lp_list[i] if i < len(lp_list) else None
        forecasts.append(HourlyForecast(
            time=t,
            weather_code=int(hourly['weather_code'][i] or 0),
            cape=float(cape_val) if cape_val is not None else 0.0,
            lightning_potential=float(lp_val) if lp_val is not None else 0.0,
        ))
        if len(forecasts) >= 6:
            break

    return WeatherData(
        location_name=location_name,
        current_temp=float(current['temperature_2m']),
        current_code=int(current['weather_code']),
        today=today,
        hourly=forecasts,
    )
