import csv
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from emporio.catalog import Catalog, CatalogDataError


class ProvidedCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = Catalog()

    def test_product_and_missing_id(self):
        product = self.catalog.get_product(95)
        self.assertEqual(product.name, "Takamine GD20 Dreadnought Natural")
        self.assertEqual(product.price_brl, Decimal("2199.00"))
        self.assertEqual(product.stock_quantity, 5)
        self.assertIsNone(self.catalog.get_product(-1))

    def test_status_and_stock(self):
        for product_id in (96, 113, 130, 136):
            with self.subTest(product_id=product_id):
                self.assertFalse(self.catalog.get_product(product_id).available)
        self.assertTrue(self.catalog.get_product(95).available)

    def test_search_normalizes_accents_and_case(self):
        matches = self.catalog.search_products("VIOLAO YAMAHA", max_price=Decimal("700"))
        self.assertEqual([p.product_id for p in matches], [81, 87])

    def test_category_and_inclusive_promotional_price(self):
        matches = self.catalog.search_products(category_id=9, max_price=Decimal("323.10"))
        self.assertIn(127, [p.product_id for p in matches])
        self.assertTrue(all(p.category_id == 9 and p.available for p in matches))
        self.assertNotIn(127, [p.product_id for p in self.catalog.search_products(
            category_id=9, max_price=Decimal("323.09"))])

    def test_inactive_promotions_and_pix_rounding(self):
        product = self.catalog.get_product(95)
        self.assertEqual(product.discount_percent, Decimal("0"))
        self.assertEqual(product.pix_price_brl, Decimal("2089.05"))
        self.assertEqual(self.catalog.get_product(81).pix_price_brl, Decimal("569.91"))

    def test_active_promotion_does_not_stack_pix(self):
        product = self.catalog.get_product(127)
        self.assertEqual(product.discount_percent, Decimal("10"))
        self.assertEqual(product.sale_price_brl, Decimal("323.10"))
        self.assertEqual(product.pix_price_brl, product.sale_price_brl)

    def test_empty_search_and_unavailable_opt_in(self):
        self.assertEqual(self.catalog.search_products("produto inexistente"), [])
        self.assertEqual(self.catalog.search_products("KA-ABP-CTG"), [])
        self.assertEqual(self.catalog.search_products("KA-ABP-CTG", available_only=False)[0].product_id, 130)

    def test_invalid_price_filter(self):
        for value in (Decimal("-1"), Decimal("NaN"), 100.0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.catalog.search_products(max_price=value)


class FixtureCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.write("categories", ["category_id", "name"], [[1, "Teste"]])
        self.write("products", ["product_id", "name", "category_id", "description", "price_brl", "stock_quantity", "status"],
                   [[1, "Instrumento", 1, "Descrição", "10.10", 1, "active"]])
        self.write("promotions", ["promotion_id", "product_id", "discount_percent", "is_active"], [])

    def write(self, name, fields, rows):
        with (self.directory / f"{name}.csv").open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(fields)
            writer.writerows(rows)

    def test_multiple_active_promotions_choose_largest(self):
        self.write("promotions", ["promotion_id", "product_id", "discount_percent", "is_active"],
                   [[1, 1, 10, 1], [2, 1, 20, 1], [3, 1, 90, 0]])
        product = Catalog(self.directory).get_product(1)
        self.assertEqual(product.sale_price_brl, Decimal("8.08"))
        self.assertEqual(product.pix_price_brl, Decimal("8.08"))

    def test_missing_file_and_ambiguous_files(self):
        path = self.directory / "products.csv"
        content = path.read_bytes()
        path.unlink()
        with self.assertRaises(CatalogDataError):
            Catalog(self.directory)
        path.write_bytes(content)
        (self.directory / "other_products.csv").write_bytes(content)
        with self.assertRaises(CatalogDataError):
            Catalog(self.directory)

    def test_missing_column_or_value(self):
        for fields, rows in [(["product_id"], [[1]]),
                             (["category_id", "name"], [[1, ""]])]:
            with self.subTest(fields=fields):
                self.write("categories", fields, rows)
                with self.assertRaises(CatalogDataError):
                    Catalog(self.directory)

    def test_invalid_promotion(self):
        for discount, active in [(101, 1), ("NaN", 1), (20, "yes")]:
            with self.subTest(discount=discount, active=active):
                self.write("promotions", ["promotion_id", "product_id", "discount_percent", "is_active"],
                           [[1, 1, discount, active]])
                with self.assertRaises(CatalogDataError):
                    Catalog(self.directory)


if __name__ == "__main__":
    unittest.main()
