"""Tests for Decimal money handling precision.

Verifies that money calculations maintain precision throughout the system.
"""

import unittest
from decimal import Decimal
from datetime import datetime


class TestMoneyPrecision(unittest.TestCase):
    """Test money handling with Decimal precision."""

    def test_decimal_multiplication(self):
        """Test that Decimal multiplication maintains precision."""
        unit_price = Decimal('10.99')
        quantity = 3

        result = unit_price * Decimal(quantity)

        self.assertEqual(result, Decimal('32.97'))
        self.assertIsInstance(result, Decimal)

    def test_decimal_addition(self):
        """Test that Decimal addition maintains precision."""
        amounts = [Decimal('10.01'), Decimal('20.02'), Decimal('30.03')]

        total = sum(amounts, Decimal('0.00'))

        self.assertEqual(total, Decimal('60.06'))
        self.assertIsInstance(total, Decimal)

    def test_no_floating_point_drift(self):
        """Test that repeated operations don't cause drift."""
        # This would fail with float: 0.1 + 0.1 + 0.1 != 0.3
        price = Decimal('0.10')

        result = price + price + price

        self.assertEqual(result, Decimal('0.30'))

    def test_decimal_rounding(self):
        """Test Decimal rounding for currency."""
        amount = Decimal('10.555')

        # Round to 2 decimal places (cents)
        rounded = amount.quantize(Decimal('0.01'))

        self.assertEqual(rounded, Decimal('10.56'))

    def test_decimal_string_conversion(self):
        """Test converting QBO string values to Decimal."""
        qbo_value = "123.45"

        decimal_value = Decimal(qbo_value)

        self.assertEqual(decimal_value, Decimal('123.45'))
        self.assertIsInstance(decimal_value, Decimal)

    def test_zero_decimal_values(self):
        """Test handling of zero values."""
        zero = Decimal('0.00')

        result = zero * Decimal(100)

        self.assertEqual(result, Decimal('0.00'))


if __name__ == '__main__':
    unittest.main()
