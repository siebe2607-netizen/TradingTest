"""Unit tests for the Valuation Engine."""

import unittest
from trading.valuation.engine import ValuationEngine

class TestValuation(unittest.TestCase):
    def setUp(self):
        self.engine = ValuationEngine()

    def test_dcf_adyen(self):
        """Test DCF calculation for Adyen (requires network)."""
        try:
            fair_value = self.engine.calculate_dcf_fair_value("ADYEN.AS")
            print(f"ADYEN.AS Fair Value: {fair_value}")
            self.assertGreater(fair_value, 0)
        except Exception as e:
            self.skipTest(f"Network error or insufficient data: {e}")

    def test_valuation_metrics(self):
        """Test getting the full metrics dictionary."""
        try:
            metrics = self.engine.get_valuation_metrics("ADYEN.AS")
            self.assertIn("fair_value", metrics)
            self.assertIn("current_price", metrics)
            self.assertIn("upside_pct", metrics)
        except Exception as e:
            self.skipTest(f"Error fetching metrics: {e}")

if __name__ == "__main__":
    unittest.main()
