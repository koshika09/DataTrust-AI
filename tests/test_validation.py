import unittest

import pandas as pd

from Data.Raw.validation import validate_data


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame(
            {
                "InvoiceNo": ["A", "B", "C", "D"],
                "Description": ["item", "return", None, "item"],
                "Quantity": [2, -1, 1, 0],
                "UnitPrice": [3.5, 3.5, 3.5, 0],
                "InvoiceDate": [
                    "2011-01-01", "2011-01-02", "2011-01-03", "invalid"
                ],
            }
        )

    def test_clean_row_is_valid_and_source_is_unchanged(self):
        source = self.data.iloc[[0]].copy()
        original = source.copy(deep=True)

        valid, review, metrics = validate_data(source)

        self.assertEqual(len(valid), 1)
        self.assertTrue(review.empty)
        self.assertEqual(metrics["total_rows"], 1)
        pd.testing.assert_frame_equal(source, original)

    def test_negative_quantity_is_review_not_called_invalid(self):
        valid, review, _ = validate_data(self.data.iloc[[1]])

        self.assertTrue(valid.empty)
        self.assertEqual(len(review), 1)
        self.assertTrue(review.iloc[0]["NegativeQuantityNeedsReview"])
        self.assertIn("possible retail return", review.iloc[0]["ReviewReason"])
        self.assertNotIn("invalid quantity", review.iloc[0]["ReviewReason"].lower())

    def test_rules_and_exactly_once_row_accounting(self):
        valid, review, metrics = validate_data(self.data)

        self.assertEqual(metrics["total_rows"], 4)
        self.assertEqual(metrics["valid_rows"] + metrics["review_rows"], 4)
        self.assertEqual(len(valid), 1)
        self.assertEqual(len(review), 3)
        self.assertTrue(set(valid.index).isdisjoint(set(review.index)))
        self.assertTrue(review.loc[2, "MissingDescription"])
        self.assertTrue(review.loc[3, "ZeroQuantityNeedsReview"])
        self.assertTrue(review.loc[3, "UnitPriceNeedsReview"])
        self.assertTrue(review.loc[3, "InvalidInvoiceDate"])

    def test_nonnumeric_quantity_and_price_are_reviewed_safely(self):
        row = pd.DataFrame(
            [{
                "Description": "item",
                "Quantity": "not-a-number",
                "UnitPrice": "bad-price",
                "InvoiceDate": "2011-01-01",
            }]
        )

        valid, review, _ = validate_data(row)

        self.assertTrue(valid.empty)
        self.assertTrue(review.iloc[0]["InvalidQuantityType"])
        self.assertTrue(review.iloc[0]["InvalidPriceType"])

    def test_missing_required_column_fails_with_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Missing required columns"):
            validate_data(self.data.drop(columns=["InvoiceDate"]))


if __name__ == "__main__":
    unittest.main()
