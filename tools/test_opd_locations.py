"""Regression tests for the build-time OPD location synchronizer."""

import copy
import datetime
import unittest

import opd_locations


TODAY = datetime.date(2026, 11, 28)

BASE_LOCATIONS = {
    "ahmedabad": {
        "name": "Bankers Vascular Hospital",
        "address": "RJP House, Ahmedabad, Gujarat 380015",
    },
    "vadodara": {
        "name": "Bankers Vascular Centre",
        "address": "Ignite Complex, Vadodara, Gujarat 390007",
    },
    "rajkot": {
        "name": "Akanksha IVF Hospital",
        "address": "Akshar Square, near Raiya Circle, Tirupati Nagar, Rajkot, Gujarat 360001",
    },
    "bhavnagar": {
        "name": "Shree Bajrangdasbapa Arogyadham",
        "address": "Chowk, Panwadi, Bhavnagar, Gujarat 364001",
    },
    "surat": {
        "name": "Old Surat Venue",
        "address": "Old Surat address, Surat, Gujarat 395003",
        "map_url": "https://www.google.com/maps/place/Metro+Hospital+-+Surat",
        "_opd_synced": True,
    },
    "rajasthan": {
        "name": "GYAYAK HOSPITAL",
        "address": "Banswara Road, Banswara, Rajasthan 327001",
    },
}


def row(date, city, hospital, address, map_url=""):
    return {
        "camp date": date,
        "city": city,
        "hospital name": hospital,
        "address": address,
        "google map link": map_url,
    }


class OpdLocationSyncTests(unittest.TestCase):
    def test_current_master_updates_only_surat(self):
        records = [
            row("25-12-2026", "Surat", "Metro Hospital",
                "Vasupujya Empire 11, 304, TGB Cir, TGB, Adajan Gam, Adajan, Surat, Gujarat 395009"),
            row("04-12-2026", "Rajkot", "Akansha Hospital",
                "Akshar square, Akanksha hospital, Near Raiya Circle, Tirupati Nagar, Rajkot, Gujarat 360001"),
            row("15-12-2026", "Bhavnagar", "Shree bajrangdasbapa",
                "Panwadi chowk, Bhavnagar, Gujarat 364001"),
        ]
        synced, report = opd_locations.sync_location_data(
            "src/products.html", copy.deepcopy(BASE_LOCATIONS),
            today=TODAY, fetch=False, source_records=records)
        self.assertEqual([item[0] for item in report["updates"]], ["surat"])
        self.assertEqual(synced["surat"]["name"], "Metro Hospital")
        self.assertEqual(synced["surat"]["postal_code"], "395009")
        self.assertEqual(synced["rajkot"]["name"], BASE_LOCATIONS["rajkot"]["name"])
        self.assertEqual(synced["bhavnagar"]["name"], BASE_LOCATIONS["bhavnagar"]["name"])
        self.assertEqual(synced["ahmedabad"], BASE_LOCATIONS["ahmedabad"])
        self.assertEqual(synced["vadodara"], BASE_LOCATIONS["vadodara"])

    def test_future_single_venue_changes_sync_all_scoped_locations(self):
        records = [
            row("02-01-2027", "Surat", "New Surat OPD",
                "1 New Road, Surat, Gujarat 395010"),
            row("03-01-2027", "Rajkot", "New Rajkot Venue",
                "1 New Road, Rajkot, Gujarat 360002"),
            row("04-01-2027", "Bhavnagar", "New Bhavnagar Venue",
                "1 New Road, Bhavnagar, Gujarat 364002"),
            row("05-01-2027", "Banswara", "New Banswara Venue",
                "1 New Road, Banswara, Rajasthan 327002"),
        ]
        synced, report = opd_locations.sync_location_data(
            "src/products.html", copy.deepcopy(BASE_LOCATIONS),
            today=TODAY, fetch=False, source_records=records)
        self.assertEqual(
            {item[0] for item in report["updates"]},
            {"surat", "rajkot", "bhavnagar", "rajasthan"},
        )
        self.assertEqual(synced["rajasthan"]["city"], "Banswara")
        self.assertIn("New+Rajkot+Venue", synced["rajkot"]["map_url"])

    def test_missing_schedule_preserves_last_verified_records(self):
        synced, report = opd_locations.sync_location_data(
            "src/products.html", copy.deepcopy(BASE_LOCATIONS),
            today=TODAY, fetch=False, source_records=[])
        self.assertEqual(synced, BASE_LOCATIONS)
        self.assertEqual(len(report["preserved"]), 4)

    def test_conflicting_map_identities_are_not_published(self):
        records = [
            row("01-12-2026", "Surat", "Metro Hospital",
                "Address A, Surat, Gujarat 395009",
                "https://www.google.com/maps/place/Metro/@21,72/data=!1s0x1:0x2"),
            row("02-12-2026", "Surat", "Metro Hospital",
                "Address B, Surat, Gujarat 395009",
                "https://www.google.com/maps/place/Other/@21,72/data=!1s0x3:0x4"),
        ]
        synced, report = opd_locations.sync_location_data(
            "src/products.html", copy.deepcopy(BASE_LOCATIONS),
            today=TODAY, fetch=False, source_records=records)
        self.assertTrue(report["issues"])
        self.assertEqual(synced["surat"], BASE_LOCATIONS["surat"])


if __name__ == "__main__":
    unittest.main()
