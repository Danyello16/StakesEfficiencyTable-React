"""Clean a daily stakes export and calculate per-promotion before/during uplift.

Run from the project root: python -m backend.analysis
"""

import csv
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def load_stakes(path: Path):
    """Return one net stake amount per (site, game, day), stored in euro cents.

    The export contains unquoted commas inside site_name. The final three fields
    are reliably game, date and stakes; the fields between site_id and game
    therefore belong to the site name.
    """
    rows = []
    repaired_rows = 0
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        if header != ["site_id", "site_name", "game", "date", "stakes_eur"]:
            raise ValueError(f"Unexpected stakes CSV header: {header}")

        for line, fields in enumerate(reader, start=2):
            if len(fields) < 5:
                raise ValueError(f"Line {line}: fewer than five CSV fields")
            if len(fields) > 5:
                repaired_rows += 1
            site_id = fields[0].strip()
            site_name = ",".join(fields[1:-3]).strip()
            game, date_str, amount_str = (value.strip() for value in fields[-3:])
            if not (site_id and site_name and game):
                raise ValueError(f"Line {line}: missing site or game identifier")
            try:
                cents = Decimal(amount_str) * 100
                if cents != cents.to_integral_value():
                    raise ValueError(f"Line {line}: stakes amount has sub-cent precision")
                cents = int(cents)
            except InvalidOperation as exc:
                raise ValueError(f"Line {line}: invalid stakes amount") from exc
            rows.append((site_id, site_name, game, date_str, cents))

    raw = pd.DataFrame(rows, columns=["site_id", "site_name", "game", "date", "cents"])
    raw["date"] = pd.to_datetime(raw["date"], format="%Y-%m-%d", errors="raise")

    # Exact repeats are duplicated daily aggregates, not additional stakes.
    duplicated_rows = int(raw.duplicated().sum())
    unique_rows = raw.drop_duplicates()
    negative_adjustments = int((unique_rows["cents"] < 0).sum())

    # Different amounts for the same site/game/date can be correction entries.
    # Sum them (including negative values), rather than keeping one arbitrarily.
    daily = (
        unique_rows.groupby(["site_id", "game", "date"], as_index=False)["cents"]
        .sum()
        .sort_values(["site_id", "game", "date"])
    )

    quality = {
        "raw_rows": len(raw),
        "unquoted_comma_rows_repaired": repaired_rows,
        "exact_duplicate_rows_removed": duplicated_rows,
        "negative_adjustments_preserved": negative_adjustments,
        "unique_daily_records": len(daily),
        "sites": int(daily["site_id"].nunique()),
        "games": int(daily["game"].nunique()),
        "data_start": daily["date"].min().date().isoformat(),
        "data_end": daily["date"].max().date().isoformat(),
    }
    return daily, quality


def _euros(cents: int) -> float:
    return float(Decimal(cents) / 100)


def _uplift(before_cents: int, during_cents: int) -> float:
    change_pct = Decimal(during_cents - before_cents) * 100 / Decimal(before_cents)
    return float(change_pct.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def build_report(data_dir: Path = ROOT / "data") -> dict:
    daily, quality = load_stakes(data_dir / "stakes_delivery.csv")
    promos = pd.read_csv(data_dir / "promos.csv", dtype={"site_id": str})
    promos["start_date"] = pd.to_datetime(promos["start_date"], errors="coerce")
    promos["end_date"] = pd.to_datetime(promos["end_date"], errors="coerce")
    games_by_site = daily.groupby("site_id")["game"].apply(set).to_dict()
    stake_by_site = {site: data for site, data in daily.groupby("site_id")}

    def selected_games(promo):
        if promo["games"].strip().upper() == "ALL":
            return games_by_site.get(promo["site_id"], set())
        return {name.strip() for name in promo["games"].split(";") if name.strip()}

    results = []
    for _, promo in promos.iterrows():
        start, end = promo["start_date"], promo["end_date"]
        games = selected_games(promo)
        result = {
            "promo_id": promo["promo_id"],
            "site_id": promo["site_id"],
            "site_name": promo["site_name"],
            "games_label": promo["games"],
            "games": sorted(games),
            "start_date": start.date().isoformat() if pd.notna(start) else None,
            "end_date": end.date().isoformat() if pd.notna(end) else None,
            "days": None,
            "before": None,
            "during": None,
            "uplift": None,
            "status": "unmeasurable",
            "reason": None,
            "before_days_present": None,
            "expected_days": None,
            "before_records": None,
            "during_records": None,
            "expected_records": None,
        }

        if pd.isna(start) or pd.isna(end) or end < start:
            result["reason"] = "Invalid promotion dates: end precedes start or a date is missing."
            results.append(result)
            continue

        days = (end - start).days + 1  # Both start and end are included.
        before_start = start - timedelta(days=days)
        before_end = start - timedelta(days=1)
        result["days"] = days
        result["expected_days"] = days
        result["expected_records"] = days * len(games)

        if not games or not games.issubset(games_by_site.get(promo["site_id"], set())):
            result["reason"] = "One or more promotion games have no data at this site."
            results.append(result)
            continue

        site_data = stake_by_site[promo["site_id"]]
        game_data = site_data[site_data["game"].isin(games)]
        before_data = game_data[game_data["date"].between(before_start, before_end)]
        during_data = game_data[game_data["date"].between(start, end)]
        before_cents = int(before_data["cents"].sum())
        during_cents = int(during_data["cents"].sum())
        result["before"] = _euros(before_cents)
        result["during"] = _euros(during_cents)
        result["before_records"] = len(before_data)
        result["during_records"] = len(during_data)
        result["before_days_present"] = int(before_data["date"].nunique())

        if len(before_data) != result["expected_records"]:
            result["reason"] = (
                f"Incomplete baseline: {len(before_data)} of "
                f"{result['expected_records']} expected site/game/day records."
            )
        elif len(during_data) != result["expected_records"]:
            result["reason"] = (
                f"Incomplete promotion period: {len(during_data)} of "
                f"{result['expected_records']} expected site/game/day records."
            )
        elif before_cents <= 0:
            result["reason"] = "Baseline stakes are zero or negative; uplift is undefined."
        else:
            # Another promotion for the same site and game in either period can
            # contaminate the comparison. Disjoint-game promotions are harmless.
            overlapping = []
            for _, other in promos.iterrows():
                if other["promo_id"] == promo["promo_id"] or other["site_id"] != promo["site_id"]:
                    continue
                if pd.isna(other["start_date"]) or pd.isna(other["end_date"]):
                    continue
                if other["end_date"] < other["start_date"]:
                    continue
                if not games.intersection(selected_games(other)):
                    continue
                if other["start_date"] <= end and other["end_date"] >= before_start:
                    overlapping.append(other["promo_id"])
            if overlapping:
                result["reason"] = "Other promotions affect these games in the comparison window: " + ", ".join(overlapping)
            else:
                result["status"] = "measurable"
                result["uplift"] = _uplift(before_cents, during_cents)

        results.append(result)

    quality["promotions"] = len(results)
    quality["measurable_promotions"] = sum(x["status"] == "measurable" for x in results)
    quality["unmeasurable_promotions"] = sum(x["status"] == "unmeasurable" for x in results)
    return {"promos": results, "quality": quality}


def export_csv(report: dict, destination: Path):
    """CSV amounts are euros; uplift is a number in percent, e.g. 12.3."""
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["promo_id", "before", "during", "uplift"])
        for result in report["promos"]:
            before = "" if result["before"] is None else f"{result['before']:.2f}"
            during = "" if result["during"] is None else f"{result['during']:.2f}"
            uplift = "" if result["uplift"] is None else f"{result['uplift']:.1f}"
            writer.writerow([result["promo_id"], before, during, uplift])


if __name__ == "__main__":
    report = build_report()
    destination = ROOT / "results.csv"
    export_csv(report, destination)
    print(f"Saved {len(report['promos'])} promotions to {destination}")
    for key, value in report["quality"].items():
        print(f"{key}: {value}")
