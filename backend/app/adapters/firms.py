import csv
import io
import httpx

from app.core.config import settings


class FirmsAdapter:
    """Adapter for NASA FIRMS Area CSV API."""

    BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

    def fetch_area_csv(
        self,
        source: str | None = None,
        bbox: str | None = None,
        day_range: int = 2,
        date: str | None = None,
    ) -> list[dict[str, str]]:
        if not settings.nasa_firms_map_key:
            raise ValueError("NASA_FIRMS_MAP_KEY is not configured.")

        src = source or settings.nasa_firms_default_source
        area = bbox or settings.nasa_firms_default_bbox
        url = f"{self.BASE_URL}/{settings.nasa_firms_map_key}/{src}/{area}/{day_range}"
        if date:
            url = f"{url}/{date}"

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url)
            resp.raise_for_status()

        reader = csv.DictReader(io.StringIO(resp.text))
        return list(reader)
