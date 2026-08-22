"""Stable Schema.org entity identifiers for Bankers Vascular Centre.

Keep these values as the sole source of truth. Generated schemas must refer to
the entities below instead of creating page-specific variations.
"""

SITE_URL = "https://bankersvascular.com"

ENTITY_IDS = {
    "website": SITE_URL + "/#website",
    "organization": SITE_URL + "/#organization",
    "ahmedabad_location": SITE_URL + "/#ahmedabad-location",
    "vadodara_location": SITE_URL + "/#vadodara-location",
    "mohal_banker": {
        "person": SITE_URL + "/our-doctors/dr-mohal-banker#person",
        "profile_page": SITE_URL + "/our-doctors/dr-mohal-banker#profilepage",
        "url": SITE_URL + "/our-doctors/dr-mohal-banker",
    },
}

# Branch facts used in structured data and matching local-page modules.  These
# values deliberately live outside individual templates so the brand and its
# two legitimate locations cannot drift apart.  Map short links are omitted:
# they are only added after their destination has been independently verified.
LOCATIONS = {
    "ahmedabad": {
        "id": ENTITY_IDS["ahmedabad_location"],
        "name": "Bankers Vascular Hospital",
        "telephone": "+91-99099-03449",
        "street_address": "2nd & 3rd Floor, RJP House, Opp. Scarlet Height Apartment, 100' Anandnagar Road, Satellite",
        "city": "Ahmedabad",
        "postal_code": "380015",
    },
    "vadodara": {
        "id": ENTITY_IDS["vadodara_location"],
        "name": "Bankers Vascular Centre",
        "telephone": "+91-99099-08428",
        "street_address": "201, 2nd Floor, Ignite Complex, Above Meera Clinic and Eye Hospital, Opp. Agrawal Cars, Near Urmi Circle, Akota",
        "city": "Vadodara",
        "postal_code": "390020",
    },
}

# Official organisation profiles linked in the shared site footer. Personal
# profiles are intentionally not inferred from these organisation accounts.
ORGANIZATION_SAME_AS = (
    "https://facebook.com/BankersVascularCentre",
    "https://youtube.com/channel/UC6UCazRbcXgkVpIP6bhk74g",
    "https://linkedin.com/company/bankersvascularcentre",
    "https://twitter.com/BankersHospital",
    "https://instagram.com/bankersvascularcentre",
)
