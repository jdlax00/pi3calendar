import requests

from .cache import ttl_cache


WMO_DESCRIPTIONS = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Freezing fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    56: "Freezing drizzle",
    57: "Freezing drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Freezing rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Light showers",
    81: "Showers",
    82: "Violent showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm w/ hail",
    99: "Thunderstorm w/ hail",
}


@ttl_cache(ttl_seconds=30 * 60)
def fetch_weather(lat: float, lon: float, timezone_name: str = "auto") -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "temperature_unit": "fahrenheit",
        "timezone": timezone_name,
        "daily": ",".join([
            "temperature_2m_max",
            "temperature_2m_min",
            "weathercode",
            "sunrise",
            "sunset",
        ]),
        "forecast_days": 8,
    }
    r = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    current = data.get("current_weather") or {}
    daily = data.get("daily") or {}
    times = daily.get("time") or []
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    codes = daily.get("weathercode") or []
    sunrises = daily.get("sunrise") or []
    sunsets = daily.get("sunset") or []

    days = []
    for i, date in enumerate(times):
        days.append({
            "date": date,
            "high_f": round(highs[i]) if i < len(highs) else None,
            "low_f": round(lows[i]) if i < len(lows) else None,
            "weather_code": codes[i] if i < len(codes) else None,
            "sunrise": sunrises[i] if i < len(sunrises) else None,
            "sunset": sunsets[i] if i < len(sunsets) else None,
        })

    return {
        "current": {
            "temp_f": round(current.get("temperature", 0)),
            "weather_code": current.get("weathercode"),
            "description": WMO_DESCRIPTIONS.get(current.get("weathercode"), ""),
        },
        "daily": days,
        "sunrise_today": days[0]["sunrise"] if days else None,
        "sunset_today": days[0]["sunset"] if days else None,
    }
