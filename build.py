#!/usr/bin/env python3
"""
The Vault — Public Data Builder
Reads vault-data.json, computes all 5 Top 10 rankings, strips purchase prices,
and writes public-data.json for the public site.

Run from C:/DerAuslander/sneakers with: python build.py
Called automatically by build.bat
"""

import json
import os
import re
from datetime import datetime, timezone

VAULT_FILE  = "vault-data.json"
PUBLIC_FILE = "public-data.json"

def parse_price(raw):
    """Strip non-numeric chars and parse as float. Returns None if invalid."""
    if not raw:
        return None
    cleaned = re.sub(r"[^0-9.]", "", str(raw))
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None

def days_between(date_a, date_b):
    """Return integer days between two ISO date strings (date_b - date_a)."""
    fmt = "%Y-%m-%d"
    return (datetime.strptime(date_b, fmt) - datetime.strptime(date_a, fmt)).days

def compute_rankings(data):
    inventory     = data.get("inventory", [])
    wear_log      = data.get("wearLog", {})
    colorway_meta = data.get("colorwayMeta", {})
    tier_meta     = data.get("tierMeta", {})
    colorway_owned = data.get("colorwayOwned", {})
    colorways     = data.get("colorways", {})

    BRONZE_EXCLUDED = "bronze"

    def tier_of(key):
        return tier_meta.get(key, "silver")

    def excluded(key):
        """Bronze tiers and unowned colorways are excluded from all rankings."""
        if tier_of(key) == BRONZE_EXCLUDED:
            return True
        if colorway_owned.get(key) is False:
            return True
        return False

    # ── 1. Most Worn ────────────────────────────────────────────────────────
    wear_counts = {}
    for shoe in inventory:
        shoe_id = shoe["id"]
        for entry in wear_log.get(str(shoe_id), wear_log.get(shoe_id, [])):
            cw  = entry["colorway"]
            key = f"{shoe_id}_{cw}"
            if excluded(key):
                continue
            if key not in wear_counts:
                wear_counts[key] = {"shoeId": shoe_id, "shoeName": shoe["name"],
                                     "shortName": shoe["shortName"], "colorway": cw,
                                     "count": 0, "lastWorn": entry["date"]}
            wear_counts[key]["count"] += 1
            if entry["date"] > wear_counts[key]["lastWorn"]:
                wear_counts[key]["lastWorn"] = entry["date"]

    def _invert_date(d):
        """Invert an ISO date string for descending sort."""
        return [-ord(c) for c in d]

    worn_ranked = sorted(
        wear_counts.values(),
        key=lambda x: (-x["count"], _invert_date(x["lastWorn"]))
    )[:10]

    # ── 2. Most Expensive ───────────────────────────────────────────────────
    price_entries = []
    for shoe in inventory:
        shoe_id = shoe["id"]
        for cw in colorways.get(shoe["shortName"], []):
            key   = f"{shoe_id}_{cw}"
            if excluded(key):
                continue
            meta  = colorway_meta.get(key, {})
            price = parse_price(meta.get("purchasePrice"))
            if price is None:
                continue
            price_entries.append({
                "shoeId": shoe_id, "shoeName": shoe["name"],
                "shortName": shoe["shortName"], "colorway": cw,
                "price": price, "purchaseDate": meta.get("purchaseDate", "")
            })

    price_ranked = sorted(
        price_entries,
        key=lambda x: (-x["price"], x["purchaseDate"])
    )[:10]

    # ── 3. Best Value (cost per wear) ───────────────────────────────────────
    value_entries = []
    for shoe in inventory:
        shoe_id = shoe["id"]
        for cw in colorways.get(shoe["shortName"], []):
            key   = f"{shoe_id}_{cw}"
            if excluded(key):
                continue
            meta  = colorway_meta.get(key, {})
            price = parse_price(meta.get("purchasePrice"))
            if price is None:
                continue
            # Count wears — wearLog keys may be int or string
            wears_list = wear_log.get(str(shoe_id), wear_log.get(shoe_id, []))
            wears = len([e for e in wears_list if e["colorway"] == cw])
            if wears == 0:
                continue
            value_entries.append({
                "shoeId": shoe_id, "shoeName": shoe["name"],
                "shortName": shoe["shortName"], "colorway": cw,
                "price": price, "wears": wears,
                "costPerWear": round(price / wears, 4)
            })

    value_ranked = sorted(
        value_entries,
        key=lambda x: (x["costPerWear"], -x["wears"])
    )[:10]

    # ── 4. Longest On Ice ───────────────────────────────────────────────────
    ice_entries = []
    for shoe in inventory:
        shoe_id = shoe["id"]
        for cw in colorways.get(shoe["shortName"], []):
            key  = f"{shoe_id}_{cw}"
            if excluded(key):
                continue
            meta = colorway_meta.get(key, {})
            purchase_date = meta.get("purchaseDate")
            if not purchase_date:
                continue
            wears_list = wear_log.get(str(shoe_id), wear_log.get(shoe_id, []))
            cw_wears   = [e for e in wears_list if e["colorway"] == cw]
            if not cw_wears:
                continue
            first_worn   = sorted(cw_wears, key=lambda e: e["date"])[0]["date"]
            days_on_ice  = days_between(purchase_date, first_worn)
            if days_on_ice < 0:
                continue
            ice_entries.append({
                "shoeId": shoe_id, "shoeName": shoe["name"],
                "shortName": shoe["shortName"], "colorway": cw,
                "daysOnIce": days_on_ice,
                "purchaseDate": purchase_date, "firstWorn": first_worn
            })

    ice_ranked = sorted(
        ice_entries,
        key=lambda x: (-x["daysOnIce"], x["purchaseDate"])
    )[:10]

    # ── 5. Longest Gap ──────────────────────────────────────────────────────
    gap_entries = []
    for shoe in inventory:
        shoe_id = shoe["id"]
        for cw in colorways.get(shoe["shortName"], []):
            key        = f"{shoe_id}_{cw}"
            if excluded(key):
                continue
            wears_list = wear_log.get(str(shoe_id), wear_log.get(shoe_id, []))
            cw_wears   = sorted(
                [e for e in wears_list if e["colorway"] == cw],
                key=lambda e: e["date"]
            )
            if len(cw_wears) < 2:
                continue
            for i in range(1, len(cw_wears)):
                from_date = cw_wears[i - 1]["date"]
                to_date   = cw_wears[i]["date"]
                gap_days  = days_between(from_date, to_date)
                if gap_days > 0:
                    gap_entries.append({
                        "shoeId": shoe_id, "shoeName": shoe["name"],
                        "shortName": shoe["shortName"], "colorway": cw,
                        "days": gap_days, "from": from_date, "to": to_date,
                        "entryKey": f"{shoe_id}_{cw}_{from_date}"
                    })

    gap_ranked = sorted(
        gap_entries,
        key=lambda x: (-x["days"], x["from"])
    )[:10]

    return {
        "wornRanked":  worn_ranked,
        "priceRanked": price_ranked,
        "valueRanked": value_ranked,
        "iceRanked":   ice_ranked,
        "gapRanked":   gap_ranked,
    }

def strip_prices(colorway_meta):
    """Return a copy of colorwayMeta with purchasePrice removed from every entry."""
    stripped = {}
    for key, meta in colorway_meta.items():
        entry = dict(meta)
        entry.pop("purchasePrice", None)
        stripped[key] = entry
    return stripped

def strip_ranking_prices(rankings):
    """Remove price/costPerWear from ranking entries so dollar amounts stay private.
    purchaseDate is stripped from price/value rankings (it's financial context) but
    preserved on iceRanked (where it's the start of the on-ice window) and gapRanked."""
    # Fields to strip per ranking — only remove purchaseDate where it implies price context
    STRIP_FIELDS = {
        "wornRanked":  ("price", "costPerWear", "purchaseDate"),
        "priceRanked": ("price", "costPerWear", "purchaseDate"),
        "valueRanked": ("price", "costPerWear", "purchaseDate"),
        "iceRanked":   ("price", "costPerWear"),
        "gapRanked":   ("price", "costPerWear"),
    }
    stripped = {}
    for key, entries in rankings.items():
        fields = STRIP_FIELDS.get(key, ("price", "costPerWear", "purchaseDate"))
        stripped[key] = []
        for entry in entries:
            clean = dict(entry)
            for f in fields:
                clean.pop(f, None)
            stripped[key].append(clean)
    return stripped

def main():
    if not os.path.exists(VAULT_FILE):
        print(f"  ERROR: {VAULT_FILE} not found. Run a BACKUP from the admin app first.")
        return

    with open(VAULT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"  Computing rankings from {VAULT_FILE}...")
    rankings = compute_rankings(data)

    # Print summary
    for label, key in [("Most Worn", "wornRanked"), ("Most Expensive", "priceRanked"),
                        ("Best Value", "valueRanked"), ("Longest On Ice", "iceRanked"),
                        ("Longest Gap", "gapRanked")]:
        print(f"    {label}: {len(rankings[key])} entries")

    # Build public data — full data minus purchasePrice, plus pre-computed rankings
    public_data = dict(data)
    public_data["colorwayMeta"] = strip_prices(data.get("colorwayMeta", {}))
    public_data["precomputedRankings"] = strip_ranking_prices(rankings)
    public_data["builtAt"] = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")

    # Remove exportedAt if present (replace with builtAt)
    public_data.pop("exportedAt", None)

    with open(PUBLIC_FILE, "w", encoding="utf-8") as f:
        json.dump(public_data, f, indent=2)

    print(f"  {PUBLIC_FILE} written successfully.")

if __name__ == "__main__":
    print(f"\n  ╔══════════════════════════════════════╗")
    print(f"  ║     THE VAULT — PUBLIC DATA BUILD    ║")
    print(f"  ╚══════════════════════════════════════╝\n")
    main()
    print()

