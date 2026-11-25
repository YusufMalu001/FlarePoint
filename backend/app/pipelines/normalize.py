import hashlib
from datetime import datetime, timezone
from typing import Any

from app.domain.models import DataOrigin, RawObservation, ValidationResult


def normalize_confidence(raw: str | None) -> float | None:
    """Normalize VIIRS (l/n/h) or MODIS (0-100) confidence to [0.0, 1.0], or None if missing."""
    if raw is None or not str(raw).strip():
        return None
    val = str(raw).strip().lower()
    if val in {"l", "low"}:
        return 0.30
    if val in {"n", "nominal"}:
        return 0.65
    if val in {"h", "high"}:
        return 0.95
    try:
        num = float(val)
        if 0.0 <= num <= 100.0:
            return round(num / 100.0, 4)
        return None
    except ValueError:
        return None


def _opt_float(val: Any) -> float | None:
    if val is None or str(val).strip() == "":
        return None
    return float(val)


def validate_and_normalize_row(
    row: dict[str, Any], source_sensor: str, origin: DataOrigin
) -> ValidationResult:
    """
    Stage 3 & 4: Schema normalization and explicit data-quality validation.
    Never invents missing values or silently converts unavailable values to zero.
    """
    errors: list[str] = []

    # Required fields
    for req in ("latitude", "longitude", "acq_date", "acq_time"):
        if req not in row or row[req] is None or str(row[req]).strip() == "":
            errors.append(f"missing_required_field:{req}")

    if errors:
        return ValidationResult(is_valid=False, errors=errors)

    # Coordinate bounds
    try:
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        if not (-90.0 <= lat <= 90.0):
            errors.append(f"latitude_out_of_bounds:{lat}")
        if not (-180.0 <= lon <= 180.0):
            errors.append(f"longitude_out_of_bounds:{lon}")
    except (ValueError, TypeError):
        errors.append("malformed_coordinates")
        lat, lon = 0.0, 0.0

    # Timestamp parsing (UTC)
    acq_date = str(row["acq_date"]).strip()
    acq_time = str(row["acq_time"]).strip().zfill(4)
    acq_ts: datetime | None = None
    try:
        acq_ts = datetime.strptime(f"{acq_date} {acq_time}", "%Y-%m-%d %H%M").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        errors.append(f"invalid_timestamp:{acq_date}_{acq_time}")

    # Optional numeric fields with range checks
    brightness: float | None = None
    try:
        raw_b = row.get("bright_ti4") if row.get("bright_ti4") not in (None, "") else row.get("brightness")
        brightness = _opt_float(raw_b)
        if brightness is not None and not (150.0 <= brightness <= 600.0):
            errors.append(f"brightness_out_of_range:{brightness}")
    except (ValueError, TypeError):
        errors.append("malformed_brightness")

    frp: float | None = None
    try:
        frp = _opt_float(row.get("frp"))
        if frp is not None and frp < 0.0:
            errors.append(f"negative_frp:{frp}")
    except (ValueError, TypeError):
        errors.append("malformed_frp")

    scan: float | None = None
    track: float | None = None
    try:
        scan = _opt_float(row.get("scan"))
        track = _opt_float(row.get("track"))
    except (ValueError, TypeError):
        errors.append("malformed_scan_track")

    if errors or acq_ts is None:
        return ValidationResult(is_valid=False, errors=errors)

    conf_raw = str(row["confidence"]).strip() if row.get("confidence") not in (None, "") else None
    conf_norm = normalize_confidence(conf_raw)
    satellite = str(row.get("satellite") or "UNKNOWN").strip()
    instrument = str(row.get("instrument") or ("MODIS" if "MODIS" in source_sensor else "VIIRS")).strip()
    daynight_raw = str(row.get("daynight") or "").strip().upper()
    daynight = daynight_raw[:1] if daynight_raw in {"D", "N", "DAY", "NIGHT"} else None
    version = str(row.get("version")).strip() if row.get("version") not in (None, "") else None

    dedup_key = f"{source_sensor}|{satellite}|{acq_ts.isoformat()}|{lat:.4f}|{lon:.4f}|{origin.value}"
    dedup_hash = hashlib.sha256(dedup_key.encode("utf-8")).hexdigest()

    obs = RawObservation(
        source_sensor=source_sensor,
        satellite=satellite,
        instrument=instrument,
        latitude=lat,
        longitude=lon,
        acq_date=acq_date,
        acq_time=acq_time,
        acq_timestamp=acq_ts,
        confidence_raw=conf_raw,
        confidence_norm=conf_norm,
        brightness=brightness,
        frp=frp,
        scan=scan,
        track=track,
        daynight=daynight,
        version=version,
        data_origin=origin,
        dedup_hash=dedup_hash,
        raw_payload=dict(row),
    )
    return ValidationResult(is_valid=True, observation=obs)
