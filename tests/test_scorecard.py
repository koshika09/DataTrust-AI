import unittest

from Data.Raw.scorecard import calculate_quality_score, build_scorecard_rows


class QualityScoreTests(unittest.TestCase):
    def test_calculates_equal_weighted_score(self):
        scores = calculate_quality_score(
            total_rows=4,
            column_count=2,
            missing_value_count=1,
            duplicate_rows=1,
            valid_rows=3,
        )

        self.assertEqual(scores["completeness"], 87.5)
        self.assertEqual(scores["duplicate_free"], 75.0)
        self.assertEqual(scores["validation_pass"], 75.0)
        self.assertAlmostEqual(scores["overall"], 79.1666667)

    def test_perfect_data_scores_one_hundred(self):
        scores = calculate_quality_score(4, 2, 0, 0, 4)

        self.assertEqual(scores["overall"], 100.0)

    def test_empty_dataset_scores_zero(self):
        scores = calculate_quality_score(0, 8, 0, 0, 0)

        self.assertEqual(scores, {
            "completeness": 0.0,
            "duplicate_free": 0.0,
            "validation_pass": 0.0,
            "overall": 0.0,
        })

    def test_impossible_missing_count_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "total cells"):
            calculate_quality_score(2, 2, 5, 0, 2)

    def test_scorecard_uses_existing_validation_rule_counts(self):
        rows = build_scorecard_rows(
            source_name="sample.xlsx",
            total_rows=4,
            column_count=2,
            missing_values={"Description": 1, "CustomerID": 1},
            duplicate_rows=1,
            metrics={
                "valid_rows": 3,
                "review_rows": 1,
                "rule_counts": {"MissingDescription": 1, "NegativeQuantityNeedsReview": 1},
            },
            run_id=7,
            output_paths=[],
        )

        rule_rows = [row for row in rows if row["category"] == "validation_rule"]
        overall = next(row for row in rows if row["category"] == "overall_score")
        limits = [row["notes"] for row in rows if row["category"] == "score_limitation"]
        self.assertEqual([row["count"] for row in rule_rows], [1, 1])
        self.assertEqual([row["percentage"] for row in rule_rows], [25.0, 25.0])
        self.assertIn("not an industry-standard score", overall["notes"])
        self.assertTrue(any("CustomerID" in note for note in limits))
        self.assertTrue(any("returns" in note for note in limits))


if __name__ == "__main__":
    unittest.main()
