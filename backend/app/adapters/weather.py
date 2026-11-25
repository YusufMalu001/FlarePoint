from typing import Any
import httpx


class WeatherAdapter:
    """Fetches current surface weather context from Open-Meteo (no API key required)."""

    URL = "https://api.open-meteo.com/v1/forecast"

    def fetch_context(self, lat: float, lon: float) -> dict[str, Any]:
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
        }
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(self.URL, params=params)
                resp.raise_for_status()
                data = resp.json().get("current", {})
                return {
                    "source": "open-meteo",
                    "temperature_c": data.get("temperature_2m"),
                    "relative_humidity_pct": data.get("relative_humidity_2m"),
                    "wind_speed_kmh": data.get("wind_speed_10m"),
                    "wind_direction_deg": data.get("wind_direction_10m"),
                }
        except Exception:
            return {
                "source": "unavailable",
                "temperature_c": None,
                "relative_humidity_pct": None,
                "wind_speed_kmh": None,
                "wind_direction_deg": None,
            }
