"""The ten PDM roles. Each role is a Django group with the same name."""

HOUSEHOLD = "Household"
GROUP_EXECUTIVE = "Enterprise group executive"
LC1_CHAIRPERSON = "LC I Chairperson"
PARISH_CHIEF = "Parish Chief"
PDC = "Parish Development Committee"
SACCO_OFFICIAL = "PDM SACCO official"
SUBCOUNTY_OFFICIAL = "Sub-county Chief and CDO"
DISTRICT_OFFICIAL = "District official"
NATIONAL_OFFICIAL = "PDM Secretariat and MoFPED"
AUDITOR = "Auditor"

ALL_ROLES = [
    HOUSEHOLD,
    GROUP_EXECUTIVE,
    LC1_CHAIRPERSON,
    PARISH_CHIEF,
    PDC,
    SACCO_OFFICIAL,
    SUBCOUNTY_OFFICIAL,
    DISTRICT_OFFICIAL,
    NATIONAL_OFFICIAL,
    AUDITOR,
]

# Roles that work across the whole country rather than inside one unit.
NATIONAL_ROLES = {NATIONAL_OFFICIAL, AUDITOR}

# Roles that can read records but never change them.
READ_ONLY_ROLES = {AUDITOR}
