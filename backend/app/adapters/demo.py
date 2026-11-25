import math
import random
from datetime import datetime, timedelta, timezone


class DemoAdapter:
    """Deterministic simulated fire observation generator (clearly marked SIMULATED_DEMO)."""

    CLUSTERS = [
        # Mediterranean coastal mountain cluster (inspired by reference coordinates)
        {"name": "Antalya-Mersin Ridge", "lat": 36.48989, "lon": 32.22333, "count": 48, "base_frp": 42.0},
        # California Sierra foothills
        {"name": "Sierra Foothills", "lat": 38.7521, "lon": -120.5142, "count": 32, "base_frp": 65.0},
        # Northern Portugal / Galicia
        {"name": "Minho-Galicia", "lat": 41.8912, "lon": -8.1245, "count": 24, "base_frp": 28.0},
    ]

    def generate_observations(self, day_range: int = 3) -> list[dict[str, str]]:
        rng = random.Random(42)
        now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        rows: list[dict[str, str]] = []

        for cluster in self.CLUSTERS:
            for i in range(cluster["count"]):
                hours_ago = rng.uniform(1, day_range * 24)
                ts = now - timedelta(hours=hours_ago)
                angle = rng.uniform(0, 2 * math.pi)
                dist_deg = rng.uniform(0.002, 0.032)
                lat = cluster["lat"] + dist_deg * math.sin(angle)
                lon = cluster["lon"] + dist_deg * math.cos(angle)
                frp = max(1.5, cluster["base_frp"] * rng.uniform(0.3, 2.8))
                brightness = 310.0 + min(90.0, frp * 0.45) + rng.uniform(-5, 5)
                conf = rng.choices(["l", "n", "h"], weights=[0.1, 0.35, 0.55])[0]
                daynight = "D" if 6 <= ts.hour <= 18 else "N"

                rows.append(
                    {
                        "latitude": f"{lat:.5f}",
                        "longitude": f"{lon:.5f}",
                        "bright_ti4": f"{brightness:.2f}",
                        "scan": "0.39",
                        "track": "0.36",
                        "acq_date": ts.strftime("%Y-%m-%d"),
                        "acq_time": ts.strftime("%H%M"),
                        "satellite": rng.choice(["N", "N20", "N21"]),
                        "instrument": "VIIRS",
                        "confidence": conf,
                        "version": "2.0NRT",
                        "frp": f"{frp:.2f}",
                        "daynight": daynight,
                    }
                )
        return rows
