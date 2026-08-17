"""Stable Schema.org entity identifiers for Bankers Vascular Centre.

Keep these values as the sole source of truth. Generated schemas must refer to
the entities below instead of creating page-specific variations.
"""

SITE_URL = "https://bankersvascular.com"

ENTITY_IDS = {
    "website": SITE_URL + "/#website",
    "organization": SITE_URL + "/#organization",
    "mohal_banker": {
        "person": SITE_URL + "/our-doctors/dr-mohal-banker#person",
        "profile_page": SITE_URL + "/our-doctors/dr-mohal-banker#profilepage",
        "url": SITE_URL + "/our-doctors/dr-mohal-banker",
    },
}

# Official organisation profiles linked in the shared site footer. Personal
# profiles are intentionally not inferred from these organisation accounts.
ORGANIZATION_SAME_AS = (
    "https://www.facebook.com/BankersVascularCentre/",
    "https://www.youtube.com/channel/UC6UCazRbcXgkVpIP6bhk74g",
    "https://www.linkedin.com/company/bankersvascularcentre",
    "https://twitter.com/BankersHospital",
    "https://www.instagram.com/bankersvascularcentre/",
)
