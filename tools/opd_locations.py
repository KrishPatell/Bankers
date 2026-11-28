"""Build-time location records derived from the shared OPD plan.

The public OPD Google Sheet is already the runtime source used by
``src/js/opd-sheet.js``.  This module reads that same sheet during a build and
uses the checked-in OPD tables in ``src/products.html`` as an offline fallback.
It deliberately stores only matching rules here; hospital names, addresses
and map URLs come from the OPD records or from the existing verified page
fallbacks in ``tools/build.py``.
"""

import csv
import datetime as _dt
import html
import io
import re
import urllib.parse
import urllib.request


MASTER_SHEET_ATTRIBUTE = "data-opd-spreadsheet-id"
SHEET_TIMEOUT_SECONDS = 8


# These are stable page/location identities, not city names.  A city can have
# more than one visiting venue (Rajkot is already an example), and Rajasthan
# is a state rather than a single city.  If the source later adds a Location
# ID column, it takes precedence over the venue anchors below.
LOCATION_RULES = {
    "surat": {
        "location_id": "surat-metro",
        "display_city": "Surat",
        "city_aliases": ("surat",),
        "venue_tokens": ("metro hospital", "metro"),
        "place_key": "0x3be04d00597a9a6b:0x520d8eb1445acdd2",
        "source_change_policy": "apply",
    },
    "rajkot": {
        "location_id": "rajkot-akanksha",
        "display_city": "Rajkot",
        "city_aliases": ("rajkot",),
        "venue_tokens": ("akansha", "akanksha"),
        "place_key": "0x3959c9eeab61fd47:0x7e9ce27badc3c800",
        "source_change_policy": "apply-if-material-change",
    },
    "bhavnagar": {
        "location_id": "bhavnagar-bajrangdasbapa",
        "display_city": "Bhavnagar",
        "city_aliases": ("bhavnagar",),
        "venue_tokens": ("bajrangdasbapa", "arogyadham"),
        "place_key": "0x395f507fdc202fa3:0x3691707e7ccef988",
        "source_change_policy": "apply-if-material-change",
    },
    "rajasthan": {
        "location_id": "rajasthan-banswara",
        "display_city": "Banswara",
        "city_aliases": ("rajasthan", "banswara"),
        "venue_tokens": ("gyayak", "banswara"),
        "required_tokens": ("banswara",),
        "source_change_policy": "apply-if-material-change",
    },
}


def _text(value):
    return " ".join(str(value or "").split()).strip()


def _key(value):
    return re.sub(r"[^a-z0-9]+", " ", _text(value).lower()).strip()


def _normalise_header(value):
    return re.sub(r"\s+", " ", _text(value).lower())


def _normalise_record(raw):
    """Convert a sheet row or fallback row to the JS OPD field names."""
    values = {_normalise_header(k): _text(v) for k, v in raw.items() if k}
    location_id = next(
        (values.get(name, "") for name in (
            "location id", "location_id", "opd location id", "stable location id",
            "opd id", "location key",
        ) if values.get(name)),
        "",
    )
    return {
        "camp date": values.get("camp date") or values.get("date") or values.get("opd date") or values.get("campdate", ""),
        "city": values.get("city", ""),
        "hospital name": values.get("hospital name", ""),
        "address": values.get("address", ""),
        "google map link": values.get("google map link", ""),
        "location id": location_id,
    }


def records_from_products_html(source_html):
    """Parse both checked-in OPD fallback tables from products.html."""
    records = []
    table_pattern = re.compile(
        r'<table\b[^>]*\bclass=["\'][^"\']*services-opd-table[^"\']*["\'][^>]*>(.*?)</table\s*>',
        re.I | re.S,
    )
    cell_pattern = re.compile(r"<t[dh]\b[^>]*>(.*?)</t[dh]\s*>", re.I | re.S)
    tag_pattern = re.compile(r"<[^>]+>")
    for table in table_pattern.findall(source_html or ""):
        for row in re.findall(r"<tr\b[^>]*>(.*?)</tr\s*>", table, re.I | re.S):
            cells = [_text(html.unescape(tag_pattern.sub(" ", cell))) for cell in cell_pattern.findall(row)]
            if len(cells) < 5 or _key(cells[0]) == "date":
                continue
            records.append(_normalise_record({
                "camp date": cells[0],
                "city": cells[1],
                "hospital name": cells[3],
                "address": cells[4],
            }))
    return [record for record in records if record["city"] and record["hospital name"]]


def records_from_csv(source_csv):
    """Parse the same CSV shape consumed by src/js/opd-sheet.js."""
    if not source_csv:
        return []
    reader = csv.DictReader(io.StringIO(source_csv.lstrip("\ufeff")))
    return [record for record in (_normalise_record(row) for row in reader)
            if record["city"] and record["hospital name"]]


def _sheet_id(source_html):
    match = re.search(
        r"\b" + re.escape(MASTER_SHEET_ATTRIBUTE) + r"\s*=\s*[\"']([^\"']+)",
        source_html or "",
        re.I,
    )
    return match.group(1).strip() if match else ""


def _sheet_name(month):
    return month.strftime("%b %y")


def _month_after(month):
    return (month.replace(day=28) + _dt.timedelta(days=4)).replace(day=1)


def _fetch_sheet(sheet_id, month, opener=None):
    query = urllib.parse.urlencode({"tqx": "out:csv", "sheet": _sheet_name(month)})
    url = "https://docs.google.com/spreadsheets/d/%s/gviz/tq?%s" % (
        urllib.parse.quote(sheet_id, safe=""), query)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Bankers-Vascular-build-opd-sync/1.0"},
    )
    open_url = opener or urllib.request.urlopen
    with open_url(request, timeout=SHEET_TIMEOUT_SECONDS) as response:
        body = response.read()
    if isinstance(body, bytes):
        body = body.decode("utf-8-sig")
    return records_from_csv(body)


def load_source_records(source_path, today=None, fetch=True, opener=None):
    """Return records from the shared sheet, with the checked-in table fallback.

    The sheet is queried only at build time.  Browsers continue to use the
    existing ``opd-sheet.js`` runtime refresh, while page location modules are
    generated from the same source on the next build.
    """
    with open(source_path, "r", encoding="utf-8") as source_file:
        source_html = source_file.read()
    fallback = records_from_products_html(source_html)
    if not fetch:
        return fallback, "checked-in OPD fallback", None
    sheet_id = _sheet_id(source_html)
    if not sheet_id:
        return fallback, "checked-in OPD fallback", "No OPD spreadsheet ID was found in products.html"
    today = today or _dt.date.today()
    month = today.replace(day=1)
    try:
        records = []
        records.extend(_fetch_sheet(sheet_id, month, opener=opener))
        records.extend(_fetch_sheet(sheet_id, _month_after(month), opener=opener))
        if records:
            return records, "shared OPD Google Sheet", None
        return fallback, "checked-in OPD fallback", "The current and next OPD sheets returned no rows"
    except (OSError, ValueError, csv.Error) as exc:
        return fallback, "checked-in OPD fallback", str(exc)


def _parse_date(value):
    value = _text(value)
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y"):
        try:
            return _dt.datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return None


def _place_key(value):
    match = re.search(r"!1s(0x[0-9a-f]+:0x[0-9a-f]+)", value or "", re.I)
    return match.group(1).lower() if match else ""


def _safe_map_url(value):
    parsed = urllib.parse.urlparse(value or "")
    if parsed.scheme == "https" and parsed.netloc.lower().endswith("google.com") and parsed.path.startswith("/maps/"):
        return value.strip()
    return ""


def _generated_map_url(record):
    # The OPD address already contains the city in the shared sheet.  Avoid
    # appending it a second time to the fallback search query.
    query = ", ".join(v for v in (
        record.get("hospital name"), record.get("address")) if v)
    return "https://www.google.com/maps/search/?api=1&query=%s" % urllib.parse.quote_plus(query)


def _city_matches(record, rule):
    city = _key(record.get("city"))
    return any(alias == city or alias in city for alias in rule["city_aliases"])


def _record_text(record):
    return _key(" ".join((record.get("hospital name", ""), record.get("address", ""), record.get("google map link", ""))))


def _record_matches(record, rule):
    if not _city_matches(record, rule):
        return False
    required = rule.get("required_tokens", ())
    if required and not all(token in _record_text(record) for token in required):
        return False
    explicit_id = _key(record.get("location id"))
    if explicit_id:
        return explicit_id.replace(" ", "-") == rule["location_id"]
    place = _place_key(record.get("google map link"))
    if place and place == rule.get("place_key", ""):
        return True
    return any(token in _record_text(record) for token in rule.get("venue_tokens", ()))


def _candidates(records, rule):
    matched = [record for record in records if _record_matches(record, rule)]
    if matched:
        return matched
    # A future venue can be matched without code changes when it is the only
    # scheduled venue in a city.  Multiple venues remain intentionally
    # ambiguous so a wrong Rajasthan/Rajkot venue is never published.
    city_rows = [record for record in records if _city_matches(record, rule)]
    if len(city_rows) == 1 and not rule.get("required_tokens"):
        return city_rows
    return []


def _select_record(records, today):
    dated = [(record, _parse_date(record.get("camp date"))) for record in records]
    future = [(record, date) for record, date in dated if date and date >= today]
    if future:
        return sorted(future, key=lambda pair: pair[1])[0][0]
    dated = [(record, date) for record, date in dated if date]
    return sorted(dated, key=lambda pair: pair[1], reverse=True)[0][0] if dated else records[-1]


def _materially_conflicting(records):
    places = {_place_key(record.get("google map link")) for record in records}
    places.discard("")
    postals = set()
    for record in records:
        match = re.search(r"\b(\d{6})\b", record.get("address", ""))
        if match:
            postals.add(match.group(1))
    return len(places) > 1 or len(postals) > 1


def _address_tokens(value):
    ignored = {"near", "road", "rd", "street", "st", "the", "and", "of", "to"}
    return {token for token in _key(value).split() if token not in ignored}


def _same_verified_venue(base, record, rule):
    place = _place_key(record.get("google map link"))
    same_place = bool(place and rule.get("place_key") and place == rule["place_key"])
    # The checked-in products fallback predates the Google Map Link column, so
    # it has no place key.  Compare its address and known venue anchor instead
    # of treating the same verified venue as a new location on every offline
    # build.  A materially different address or venue still returns False.
    base_tokens = _address_tokens(base.get("address"))
    source_tokens = _address_tokens(record.get("address"))
    if not base_tokens or not source_tokens:
        return same_place
    overlap = len(base_tokens & source_tokens) / float(max(len(base_tokens), len(source_tokens)))
    name_text = _key(" ".join((base.get("name", ""), record.get("hospital name", ""))))
    known_tokens = rule.get("venue_tokens", ())
    name_is_known = any(token in name_text for token in known_tokens)
    return overlap >= 0.7 and name_is_known and (same_place or not place)


def _location_from_record(base, record, rule):
    name = _text(record.get("hospital name"))
    address = _text(record.get("address"))
    verified_map = base.get("map_url") if _same_verified_venue(base, record, rule) else ""
    map_url = (_safe_map_url(record.get("google map link"))
               or _safe_map_url(verified_map)
               or _generated_map_url(record))
    postal_match = re.search(r"\b(\d{6})\b", address)
    result = dict(base)
    result.update({
        "eyebrow": "%s consultation location" % rule["display_city"],
        "heading": "Visit us at %s" % name,
        "name": name,
        "address": address,
        "city": rule["display_city"],
        "postal_code": postal_match.group(1) if postal_match else base.get("postal_code", ""),
        "map_url": map_url,
        "map_embed_url": "https://www.google.com/maps?q=%s&output=embed" % urllib.parse.quote_plus(
            ", ".join(v for v in (name, address) if v)),
        "source_location_id": rule["location_id"],
        "source_place_key": _place_key(map_url),
        "_opd_synced": True,
    })
    return result


def sync_location_data(source_path, base_locations, today=None, fetch=True, opener=None, source_records=None):
    """Synchronize build location records and return a diagnostic report.

    ``source_records`` is intentionally supported for deterministic tests: it
    lets tests simulate future sheet changes without writing to production
    data.  A normal build leaves it unset and reads the shared OPD source.
    """
    today = today or _dt.date.today()
    if source_records is None:
        records, source_name, source_error = load_source_records(
            source_path, today=today, fetch=fetch, opener=opener)
    else:
        records, source_name, source_error = list(source_records), "simulated OPD source", None
    records = [_normalise_record(record) for record in records]
    synced = {city: dict(location) for city, location in base_locations.items()}
    report = {
        "source": source_name,
        "source_error": source_error,
        "updates": [],
        "preserved": [],
        "issues": [],
        "records": records,
    }
    for city, rule in LOCATION_RULES.items():
        if city not in synced:
            continue
        candidates = _candidates(records, rule)
        if not candidates:
            report["preserved"].append((city, "no unambiguous scheduled venue; retained last verified details"))
            continue
        if _materially_conflicting(candidates):
            report["issues"].append(
                "%s has multiple OPD map identities; retained the last verified location" % city)
            continue
        selected = _select_record(candidates, today)
        if (rule["source_change_policy"] == "apply-if-material-change"
                and _same_verified_venue(synced[city], selected, rule)):
            report["preserved"].append((city, "master record is the existing verified venue"))
            continue
        synced[city] = _location_from_record(synced[city], selected, rule)
        report["updates"].append((city, synced[city]["name"], synced[city]["address"]))
    return synced, report
