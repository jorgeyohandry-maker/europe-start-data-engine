#!/usr/bin/env python3
"""
Europe Start — Free Eurostat Data Engine
----------------------------------------
Fetches Eurostat Statistics API data using a verified mapping registry,
normalizes JSON-stat responses into long-form CSV, validates provenance,
and produces an import-ready file for Europe Start.

No Base44 credentials are required. The engine runs locally or in CI.

IMPORTANT:
- Only mappings explicitly marked VERIFIED in mappings.csv are eligible.
- "VERIFIED" means the dataset/dimension configuration was verified against
  the Eurostat API; it does NOT mean the stored Base44 values are live.
- The engine never invents dataset codes or dimension filters.
"""

import csv, json, sys, time
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
ROOT = Path(__file__).resolve().parent
MAPPING_FILE = ROOT / "mappings.csv"
COUNTRY_FILE = ROOT / "countries.csv"
OUT_DIR = ROOT / "output"
OUT_DIR.mkdir(exist_ok=True)

def now_utc():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def load_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def api_get(dataset, params):
    query = urlencode(params, doseq=True)
    url = BASE_URL + dataset + "?" + query
    req = Request(url, headers={"User-Agent": "EuropeStart-EurostatEngine/0.1"})
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def ordered_values(dim):
    idx = dim.get("category", {}).get("index", {})
    if isinstance(idx, dict):
        return [k for k, _ in sorted(idx.items(), key=lambda kv: kv[1])]
    if isinstance(idx, list):
        return idx
    return list(dim.get("category", {}).get("label", {}).keys())

def jsonstat_to_rows(payload, mapping, retrieved_at):
    dims = payload.get("id", [])
    sizes = payload.get("size", [])
    if not dims or not sizes:
        raise ValueError("Eurostat response has no usable dimensions.")

    values = payload.get("value", {})
    if isinstance(values, list):
        flat = {i: v for i, v in enumerate(values) if v is not None}
    else:
        flat = values

    dim_values = {d: ordered_values(payload["dimension"][d]) for d in dims}
    rows = []

    def unravel(n, sizes):
        coords = [0] * len(sizes)
        for i in range(len(sizes) - 1, -1, -1):
            coords[i] = n % sizes[i]
            n //= sizes[i]
        return coords

    for flat_index, value in flat.items():
        coords = unravel(int(flat_index), sizes)
        record = {
            "indicator": mapping["indicator"],
            "dataset_code": mapping["dataset_code"],
            "source": "Eurostat",
            "source_url": BASE_URL + mapping["dataset_code"],
            "verification_status": "VERIFIED_MAPPING",
            "data_status": "LIVE_CANDIDATE",
            "retrieved_at": retrieved_at,
            "publication_date": payload.get("updated"),
        }
        for dim, pos in zip(dims, coords):
            record[dim] = dim_values[dim][pos]
        record["value"] = value
        record["unit"] = mapping.get("unit", "")
        record["notes"] = "Retrieved directly from Eurostat Statistics API."
        rows.append(record)
    return rows

def main():
    mappings = load_csv(MAPPING_FILE)
    countries = {r["iso2"] for r in load_csv(COUNTRY_FILE)}

    eligible = []
    skipped = []
    for m in mappings:
        if m["status"].strip().upper() != "VERIFIED":
            skipped.append((m["indicator"], "mapping status is not VERIFIED"))
            continue
        if not m["dataset_code"].strip():
            skipped.append((m["indicator"], "missing dataset_code"))
            continue
        eligible.append(m)

    if not eligible:
        raise SystemExit("No VERIFIED mappings available. Update mappings.csv first.")

    all_rows = []
    errors = []
    retrieved_at = now_utc()

    for m in eligible:
        try:
            # query_params_json contains the exact verified Eurostat filters.
           params = json.loads(m["query_params_json"])

params.setdefault("lang", "EN")

# Restrict the request to Europe Start controlled-test countries.
params["geo"] = sorted(countries)

payload = api_get(m["dataset_code"], params)
            rows = jsonstat_to_rows(payload, m, retrieved_at)

            # If geo exists, retain only Europe Start countries.
            if "geo" in params:
                rows = [r for r in rows if r.get("geo") in countries]

            all_rows.extend(rows)
            print(f"OK  {m['indicator']} -> {m['dataset_code']} ({len(rows)} rows)")
        except Exception as e:
            errors.append((m["indicator"], str(e)))
            print(f"ERR {m['indicator']} -> {m['dataset_code']}: {e}")

    out = OUT_DIR / f"europe_start_eurostat_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.csv"
    if all_rows:
        keys = sorted({k for r in all_rows for k in r})
        with out.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(all_rows)

    manifest = OUT_DIR / "last_run_manifest.json"
    manifest.write_text(json.dumps({
        "engine_version": "0.1",
        "retrieved_at": retrieved_at,
        "source": "Eurostat Statistics API",
        "verified_mappings_attempted": len(eligible),
        "rows_written": len(all_rows),
        "skipped": skipped,
        "errors": errors,
        "live_data_written_to_base44": False,
        "note": "This run creates an import artifact; it does not modify Base44."
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nWrote: {out}")
    print(f"Rows: {len(all_rows)}")
    print(f"Errors: {len(errors)}")
    if errors:
        sys.exit(2)

if __name__ == "__main__":
    main()
