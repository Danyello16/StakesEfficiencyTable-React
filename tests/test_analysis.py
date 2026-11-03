"""Run: python -m unittest discover -s tests -v"""
import csv
import re
import tempfile
import unittest
from pathlib import Path

from backend.analysis import ROOT, build_report, export_csv, load_stakes


class PromoAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.by_id = {row["promo_id"]: row for row in cls.report["promos"]}

    def test_repairs_export_and_preserves_adjustments(self):
        daily, quality = load_stakes(ROOT / "data" / "stakes_delivery.csv")
        self.assertEqual(quality["raw_rows"], 81692)
        self.assertEqual(quality["unquoted_comma_rows_repaired"], 2562)
        self.assertEqual(quality["exact_duplicate_rows_removed"], 39)
        self.assertEqual(quality["negative_adjustments_preserved"], 12)
        self.assertEqual(len(daily), 81641)
        adjusted = daily[(daily["site_id"] == "1004") & (daily["game"] == "Lucky Lantern") & (daily["date"] == "2026-07-17")]
        self.assertEqual(int(adjusted.iloc[0]["cents"]), 264415)  # 2680.74 - 36.59

    def test_all_promos_included(self):
        self.assertEqual(len(self.report["promos"]), 120)
        self.assertEqual(self.report["quality"]["measurable_promotions"], 118)

    def test_multi_game_promo(self):
        promo = self.by_id["P01"]
        self.assertEqual(promo["days"], 7)
        self.assertEqual(promo["expected_records"], 14)
        self.assertEqual((promo["before"], promo["during"], promo["uplift"]), (10330.27, 13645.02, 32.1))

    def test_unquoted_comma_site_name(self):
        promo = self.by_id["P02"]  # Casino Beta, DE: site name is split in the source export.
        self.assertEqual((promo["before"], promo["during"], promo["uplift"]), (3494.32, 4154.51, 18.9))

    def test_all_games_and_exact_duplicates(self):
        promo = self.by_id["P04"]
        self.assertEqual(len(promo["games"]), 13)
        self.assertEqual((promo["before"], promo["during"], promo["uplift"]), (120403.41, 136922.69, 13.7))

    def test_invalid_dates_are_not_measured(self):
        promo = self.by_id["P05"]
        self.assertEqual(promo["status"], "unmeasurable")
        self.assertIsNone(promo["uplift"])
        self.assertIsNone(promo["before"])

    def test_new_game_has_incomplete_baseline(self):
        promo = self.by_id["P07"]
        self.assertEqual(promo["before_days_present"], 1)
        self.assertEqual(promo["expected_days"], 7)
        self.assertEqual(promo["before"], 936.99)  # Partial observed sum, not valid baseline.
        self.assertEqual(promo["during"], 9063.78)
        self.assertIsNone(promo["uplift"])
        self.assertEqual(promo["status"], "unmeasurable")

    def test_results_csv_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            generated_path = Path(directory) / "results.csv"
            export_csv(self.report, generated_path)
            with generated_path.open(encoding="utf-8", newline="") as handle:
                generated_reader = csv.DictReader(handle)
                self.assertEqual(generated_reader.fieldnames, ["promo_id", "before", "during", "uplift"])
                generated_rows = list(generated_reader)

        with (ROOT / "results.csv").open(encoding="utf-8", newline="") as handle:
            submitted_reader = csv.DictReader(handle)
            self.assertEqual(submitted_reader.fieldnames, ["promo_id", "before", "during", "uplift"])
            submitted_rows = list(submitted_reader)

        self.assertEqual(generated_rows, submitted_rows)
        self.assertEqual(len(generated_rows), 120)
        self.assertEqual(len({row["promo_id"] for row in generated_rows}), 120)

        money_pattern = re.compile(r"^-?\d+\.\d{2}$")
        uplift_pattern = re.compile(r"^-?\d+\.\d$")
        for row in generated_rows:
            if row["before"]:
                self.assertRegex(row["before"], money_pattern)
            if row["during"]:
                self.assertRegex(row["during"], money_pattern)
            if row["uplift"]:
                self.assertRegex(row["uplift"], uplift_pattern)

        by_id = {row["promo_id"]: row for row in generated_rows}
        self.assertEqual(by_id["P05"], {"promo_id": "P05", "before": "", "during": "", "uplift": ""})
        self.assertEqual(by_id["P07"]["uplift"], "")


if __name__ == "__main__":
    unittest.main()
