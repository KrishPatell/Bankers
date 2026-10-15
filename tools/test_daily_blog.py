"""Offline unit checks for the Google-sheet automation helpers."""

import unittest
from datetime import date

from tools import daily_blog


class DailyBlogHelpersTest(unittest.TestCase):
    def test_sheet_dates_use_day_first_format(self):
        self.assertEqual(daily_blog.parse_date("15/10/2026"), date(2026, 10, 15))
        self.assertEqual(daily_blog.parse_date("2026-10-15"), date(2026, 10, 15))

    def test_real_sheet_headers_are_mapped(self):
        row = {
            "Blog date": "15/10/2026",
            "BLOG TITLE": "What Does an Interventional Radiologist Do?",
            "DR. NAME": "DR.TENSI",
            "Doc ID": "1H3uF0aL5MMy9zJDVvUq5hbORfDRTvsEXrJuhZOPqMGc",
            "Meta tile": "Approved title",
            "meta discripation": "Approved description",
            "_row_number": "16",
            "_sheet_id": "sheet-id",
            "_sheet_name": "OCT-2026",
            "_source_key": "sheet-id:OCT-2026:16",
        }
        item = daily_blog.sheet_item(row)
        self.assertEqual(item["scheduled_date"], "2026-10-15")
        self.assertEqual(item["author_label"], "DR.TENSI")
        self.assertEqual(item["doc_id"], "1H3uF0aL5MMy9zJDVvUq5hbORfDRTvsEXrJuhZOPqMGc")

    def test_title_and_slug_are_stable(self):
        title = "What Does an Interventional Radiologist Do? Conditions Treated Without Major Surgery"
        self.assertEqual(
            daily_blog.slugify(title),
            "what-does-an-interventional-radiologist-do-conditions-treated-without-major-surgery",
        )


if __name__ == "__main__":
    unittest.main()
