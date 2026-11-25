import hashlib
from datetime import datetime, timezone

from app.domain.models import DataOrigin, RawObservation


def normalize_confidence(raw: str) -> float:
    """Normalize VIIRS (l/n/h) or MODIS (0-100) confidence to [0.0, 1.0]."""
    val = raw.strip().lower()
    if val in {"l", "low"}:
        return 0.30
    if val in {"n", "nominal"}:
        return 0.65
    if val in {"h", "high"}:
        return 0.95
    try:
        num = float(val)
        return max(0.0, min(1.0, num / 100.0))
    except ValueError:
        return 0.50


def normalize_row(row: dict[str, str], source_sensor: str, origin: DataOrigin) -> RawObservation | None:
    """Validate and normalize a single FIRMS-format CSV row."""
    try:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return None

        acq_date = row["acq_date"].strip()
        acq_time = row["acq_time"].strip().zfill(4)
        acq_ts = datetime.strptime(f"{acq_date} {acq_time}", "%Y-%m-%d %H%M").replace(
            tzinfo=timezone.utc
        )

        brightness = float(row.get("bright_ti4") or row.get("brightness") or 300.0)
        frp = max(0.0, float(row.get("frp") or 0.0))
        conf_raw = str(row.get("confidence", "n")).strip()
        conf_norm = normalize_confidence(conf_raw)
        satellite = str(row.get("satellite", "UNKNOWN")).strip()
        daynight = str(row.get("daynight", "D")).strip()[:1].upper() or "D"

        dedup_key = f"{source_sensor}|{satellite}|{acq_ts.isoformat()}|{lat:.4f}|{lon:.4f}|{origin.value}"
        dedup_hash = hashlib.sha256(dedup_key.encode("utf-8")).hexdigest()

        return RawObservation(
            source_sensor=source_sensor,
            satellite=satellite,
            latitude=lat,
            longitude=lon,
            acq_timestamp=acq_ts,
            brightness=brightness,
            frp=frp,
            confidence_raw=conf_raw,
            confidence_norm=conf_norm,
            daynight=daynight,
            data_origin=origin,
            dedup_hash=dedup_hash,
            scan=float(row["scan"]) if row.get("scan") else None,
            track=float(row["track"]) if row.get("track") else None,
        )
    except (KeyError, ValueError, TypeError):
        return None
