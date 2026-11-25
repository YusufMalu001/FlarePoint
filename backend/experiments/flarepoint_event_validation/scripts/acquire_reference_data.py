import json
from datetime import datetime, timezone
from pathlib import Path
import httpx
import yaml
from shapely.geometry import shape

VAL_DIR = Path(__file__).resolve().parent.parent


def acquire_wfigs_perimeters() -> Path:
    cfg = yaml.safe_load((VAL_DIR / "validation_config.yaml").read_text())
    west, south, east, north = cfg["region"]["bbox_wgs84"]
    url = cfg["reference"]["url"]
    params = {
        "where": "attr_UniqueFireIdentifier LIKE '2024-%'",
        "geometry": f"{west},{south},{east},{north}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "poly_IncidentName,attr_UniqueFireIdentifier,attr_FireDiscoveryDateTime,attr_ContainmentDateTime,attr_ControlDateTime,poly_GISAcres,attr_POOProtectingAgency",
        "f": "geojson",
    }
    resp = httpx.get(url, params=params, timeout=30.0)
    resp.raise_for_status()
    geojson = resp.json()

    valid_features = []
    invalid_geom = 0
    for feat in geojson.get("features", []):
        geom = feat.get("geometry")
        if not geom:
            invalid_geom += 1
            continue
        shp = shape(geom)
        if not shp.is_valid or shp.is_empty:
            shp = shp.buffer(0)
        if shp.is_empty:
            invalid_geom += 1
            continue
        valid_features.append(feat)

    data_dir = VAL_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_path = data_dir / "wfigs_2024_norcal.geojson"
    out_path.write_text(json.dumps({"type": "FeatureCollection", "features": valid_features}))

    manifest = {
        "source_name": cfg["reference"]["source_name"],
        "url": url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "crs": "EPSG:4326",
        "features_valid": len(valid_features),
        "features_invalid_skipped": invalid_geom,
    }
    (data_dir / "reference_manifest.json").write_text(json.dumps(manifest, indent=2))
    return out_path


if __name__ == "__main__":
    p = acquire_wfigs_perimeters()
    print("Saved reference perimeters to:", p)
