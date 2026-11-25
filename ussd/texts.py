"""Every USSD screen text, in English and Luganda.

`t(lang, key, **values)` returns the text in the household's language,
falling back to English. To correct a translation, change it here; the
menu logic in menu.py does not need to change.

The Luganda was drafted for this system and should be checked by a
native speaker before real use.
"""

TEXTS = {
    "en": {
        "menu": "PDM Services\n{name}\n1. My PDM status\n2. My loan\n3. Report a problem\n4. Track a complaint\n0. Luganda",
        "not_registered": "This number is not registered under PDM. Visit your Parish Chief to be profiled.",
        "invalid": "Invalid choice. Please dial again.",
        # status
        "village": "Village: {village}",
        "verified": "Verified by LC I",
        "pending": "Waiting for LC I to verify",
        "rejected": "Not verified: {note}",
        "group": "Group: {group}",
        "no_group": "Not yet in an enterprise group",
        "sacco": "SACCO: {sacco}",
        # loan
        "no_loan": "You have no PDM loan application. Ask your enterprise group executive.",
        "loan_draft": "Loan of {amount} is a draft with your group executive.",
        "loan_waiting": "Loan of {amount} is with {sacco} for a decision.",
        "loan_approved": "Loan of {amount} is approved. {sacco} will pay it out soon.",
        "loan_rejected": "Loan of {amount} was not approved. Reason: {reason}",
        "loan_closed": "Loan of {amount} is fully repaid. Thank you.",
        "loan": "Loan {amount}",
        "repaid": "Repaid UGX {value}",
        "balance": "Balance UGX {value}",
        "overdue": "Overdue UGX {value} ({days} days)",
        "next": "Next UGX {value} by {date}",
        "defaulted": "In default: visit your SACCO.",
        # complaints
        "categories": "Problem is about:\n{options}",
        "describe": "Describe the problem in a few words:",
        "too_short": "Please dial again and describe the problem.",
        "received": "Received. Ref {reference}. You will get an answer within 7 days. PDM services are free.",
        "ask_reference": "Enter your complaint number (the digits after PDM-):",
        "no_complaint": "No complaint with that number for this phone.",
        "complaint_status": "{reference}: {status}",
        "with_office": "With the {level} office",
        "reply": "Reply: {message}",
    },
    "lg": {
        "menu": "Obuweereza bwa PDM\n{name}\n1. Embeera yange mu PDM\n2. Looni yange\n3. Loopa ekizibu\n4. Goberera okwemulugunya\n0. English",
        "not_registered": "Ennamba eno tewandiisibwa mu PDM. Genda eri Omukulu w'Omuluka akuwandiike.",
        "invalid": "Ky'olonze si kituufu. Kuba nate.",
        "village": "Ekyalo: {village}",
        "verified": "LC I akakasizza",
        "pending": "Olinda LC I okukakasa",
        "rejected": "Tokakasiddwa: {note}",
        "group": "Ekibiina: {group}",
        "no_group": "Tonnayingira kibiina",
        "sacco": "SACCO: {sacco}",
        "no_loan": "Tolina kusaba looni ya PDM. Buuza omukulembeze w'ekibiina kyo.",
        "loan_draft": "Looni ya {amount} ekyali mu ntegeka n'omukulembeze w'ekibiina.",
        "loan_waiting": "Looni ya {amount} eri ne {sacco} okusalawo.",
        "loan_approved": "Looni ya {amount} ekkiriziddwa. {sacco} ejja kugikuwa mangu.",
        "loan_rejected": "Looni ya {amount} tekkiriziddwa. Ensonga: {reason}",
        "loan_closed": "Looni ya {amount} ogisasudde yonna. Webale.",
        "loan": "Looni {amount}",
        "repaid": "Osasudde UGX {value}",
        "balance": "Ekisigadde UGX {value}",
        "overdue": "Ebibuze UGX {value} (ennaku {days})",
        "next": "Ekiddako UGX {value} nga {date}",
        "defaulted": "Looni eremereddwa: genda ku SACCO yo.",
        "categories": "Ekizibu kikwata ku:\n{options}",
        "describe": "Nnyonnyola ekizibu mu bigambo bitono:",
        "too_short": "Kuba nate onnyonnyole ekizibu.",
        "received": "Kifunidwa. Namba {reference}. Ojja kuddibwamu mu nnaku 7. Obuweereza bwa PDM bwa bwerere.",
        "ask_reference": "Yingiza namba y'okwemulugunya kwo (ennamba eziri oluvannyuma lwa PDM-):",
        "no_complaint": "Tewali kwemulugunya na namba eyo ku ssimu eno.",
        "complaint_status": "{reference}: {status}",
        "with_office": "Kuli mu wofiisi ya {level}",
        "reply": "Okuddibwamu: {message}",
    },
}

# Short labels for the complaint categories, in the same order as the menu numbers.
CATEGORY_LABELS = {
    "en": ["Loan delayed", "Left out or rejected", "Repayment record", "SACCO or official", "Asked for a bribe", "Other"],
    "lg": ["Looni eruddewo", "Nalekebwa oba nagaanibwa", "Okusasula kwange", "SACCO oba omukungu", "Bansaba enguzi", "Ekirala"],
}

# Complaint statuses and offices, as households would say them.
WORDS = {
    "en": {"open": "Open", "in_progress": "Being handled", "resolved": "Resolved",
           "parish": "parish", "subcounty": "sub-county", "district": "district"},
    "lg": {"open": "Kiggule", "in_progress": "Kikolebwako", "resolved": "Kigonjoddwa",
           "parish": "muluka", "subcounty": "ggombolola", "district": "disitulikiti"},
}


def t(lang, key, **values):
    """The text for `key` in `lang` (English if missing), with values filled in."""
    text = TEXTS.get(lang, TEXTS["en"]).get(key) or TEXTS["en"][key]
    return text.format(**values)


def word(lang, key):
    return WORDS.get(lang, WORDS["en"])[key]
