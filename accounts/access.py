"""The access policy: which role may open which part of the system, and do what.

This is the one place that decides access (least privilege). Views take
their `allowed_roles` from here, the menu and each user's home page are
built from it, and the tests check that every menu link opens and every
other page is refused. To change who can do something, change it here.

Area scoping is separate and still applies everywhere: a role that may open
a page sees only the records inside the user's own area.
"""

from dataclasses import dataclass

from accounts import roles as r


@dataclass(frozen=True)
class Feature:
    key: str
    label: str
    url_name: str  # where the feature starts (a menu link); "" for actions done on a record
    roles: tuple
    description: str

    @property
    def icon(self):
        """Bootstrap Icons name for the menu and home page."""
        return ICONS.get(self.key, "circle")


# Pages a role can open. Order is the order of the menu.
PAGES = [
    Feature("my_household", "My household", "my_household", (r.HOUSEHOLD,),
            "Your household's PDM status, your loan, repayments and SMS alerts."),
    Feature("dashboard", "Dashboard", "dashboard",
            (r.PARISH_CHIEF, r.PDC, r.SACCO_OFFICIAL, r.SUBCOUNTY_OFFICIAL, r.DISTRICT_OFFICIAL,
             r.NATIONAL_OFFICIAL, r.AUDITOR),
            "Totals and charts for your area."),
    Feature("households", "Households", "registry:household_list",
            (r.LC1_CHAIRPERSON, r.GROUP_EXECUTIVE, r.PARISH_CHIEF, r.PDC, r.SACCO_OFFICIAL,
             r.SUBCOUNTY_OFFICIAL, r.AUDITOR),
            "Household profiles in your area, with NINs and verification."),
    Feature("groups", "Groups", "registry:group_list",
            (r.GROUP_EXECUTIVE, r.PARISH_CHIEF, r.PDC, r.SACCO_OFFICIAL, r.SUBCOUNTY_OFFICIAL, r.AUDITOR),
            "Enterprise groups and their members."),
    Feature("saccos", "SACCOs", "saccos:sacco_list",
            (r.PARISH_CHIEF, r.PDC, r.SACCO_OFFICIAL, r.SUBCOUNTY_OFFICIAL, r.DISTRICT_OFFICIAL,
             r.NATIONAL_OFFICIAL, r.AUDITOR),
            "PDM SACCOs, their eligibility checklist and fund releases."),
    Feature("loans", "Loans", "loans:loan_list",
            (r.GROUP_EXECUTIVE, r.PARISH_CHIEF, r.PDC, r.SACCO_OFFICIAL, r.SUBCOUNTY_OFFICIAL,
             r.DISTRICT_OFFICIAL, r.NATIONAL_OFFICIAL, r.AUDITOR),
            "Parish Revolving Fund loans from application to repayment."),
    Feature("arrears", "Arrears", "loans:arrears_list",
            (r.PARISH_CHIEF, r.PDC, r.SACCO_OFFICIAL, r.SUBCOUNTY_OFFICIAL, r.DISTRICT_OFFICIAL,
             r.NATIONAL_OFFICIAL, r.AUDITOR),
            "Loans with instalments overdue, and defaults."),
    Feature("quarterly_report", "Reports", "quarterly_report",
            (r.SUBCOUNTY_OFFICIAL, r.DISTRICT_OFFICIAL, r.NATIONAL_OFFICIAL, r.AUDITOR),
            "The quarterly PDM report for your area, printable to PDF."),
    Feature("complaints", "Complaints", "feedback:complaint_list",
            (r.PARISH_CHIEF, r.PDC, r.SUBCOUNTY_OFFICIAL, r.DISTRICT_OFFICIAL, r.NATIONAL_OFFICIAL, r.AUDITOR),
            "Complaints from households in your area, their responses and escalations."),
    Feature("stories", "Stories", "feedback:story_list",
            (r.PARISH_CHIEF, r.PDC, r.SUBCOUNTY_OFFICIAL, r.AUDITOR),
            "Success stories: drafts, consent, the PDC's checks and what is published."),
    Feature("ussd_simulator", "USSD", "ussd:simulator",
            (r.HOUSEHOLD, r.LC1_CHAIRPERSON, r.PARISH_CHIEF, r.SUBCOUNTY_OFFICIAL),
            "The PDM USSD menu on a phone screen: status, loan and complaints. Households use their own number."),
    Feature("audit_log", "Audit log", "audit_log", (r.AUDITOR,),
            "Every change to every record, read-only, with CSV download."),
    Feature("sign_in_log", "Sign-ins", "sign_in_log", (r.AUDITOR,),
            "Every sign-in attempt, including failed ones and locked accounts."),
]

# Things a role can do. Each is checked again by its own view.
ACTIONS = [
    Feature("register_household", "Register a household", "registry:household_create", (r.PARISH_CHIEF,),
            "Profile a household, with NIN and wealth rank."),
    Feature("verify_household", "Verify households", "", (r.LC1_CHAIRPERSON,),
            "Confirm or reject that a household lives in your village; a rejection needs a reason."),
    Feature("register_group", "Register an enterprise group", "registry:group_create", (r.SUBCOUNTY_OFFICIAL,),
            "Register a group and link it to the parish SACCO."),
    Feature("apply_loan", "Start a loan application", "loans:loan_create", (r.GROUP_EXECUTIVE,),
            "Apply for a verified member (up to UGX 1,000,000) and submit it to the SACCO."),
    Feature("tick_checklist", "Update the SACCO checklist", "", (r.SACCO_OFFICIAL,),
            "Tick the eligibility requirements your SACCO meets."),
    Feature("appraise_loan", "Appraise, decide and pay out loans", "", (r.SACCO_OFFICIAL,),
            "Score applications, approve or reject with reasons, record payouts and repayments."),
    Feature("raise_complaint", "Raise a complaint", "feedback:complaint_create", (r.HOUSEHOLD,),
            "Tell the PDM office about a problem; you get a reference number by SMS."),
    Feature("respond_complaint", "Respond to complaints", "",
            (r.PARISH_CHIEF, r.SUBCOUNTY_OFFICIAL, r.DISTRICT_OFFICIAL),
            "Answer complaints at your level; unresolved ones move up after 7 days."),
    Feature("draft_story", "Draft a success story", "feedback:story_create", (r.PARISH_CHIEF, r.SUBCOUNTY_OFFICIAL),
            "Write up a household's success and record their consent to publish it."),
    Feature("check_story", "Check success stories", "", (r.PDC,),
            "Check each story against the household's records, then approve it or send it back."),
    Feature("record_release", "Record fund releases", "", (r.NATIONAL_OFFICIAL,),
            "Record Parish Revolving Fund transfers to eligible SACCOs."),
    Feature("confirm_release", "Confirm fund releases", "", (r.DISTRICT_OFFICIAL,),
            "Confirm that released funds reached the SACCO's account."),
]

# Icons (https://icons.getbootstrap.com) for each page and action.
ICONS = {
    "my_household": "house-heart", "dashboard": "speedometer2", "households": "people", "groups": "diagram-3",
    "saccos": "bank", "loans": "cash-coin", "arrears": "exclamation-triangle", "quarterly_report": "file-earmark-bar-graph",
    "complaints": "megaphone", "stories": "stars", "ussd_simulator": "phone", "audit_log": "shield-check",
    "sign_in_log": "key", "register_household": "person-plus", "verify_household": "patch-check",
    "register_group": "people-fill", "apply_loan": "file-earmark-plus", "tick_checklist": "list-check",
    "appraise_loan": "clipboard-check", "raise_complaint": "chat-left-text", "respond_complaint": "reply",
    "draft_story": "pencil-square", "check_story": "check2-circle", "record_release": "send", "confirm_release": "check2-all",
}

_ALL = {feature.key: feature for feature in PAGES + ACTIONS}


def roles_for(key):
    """The roles allowed to use a feature, for a view's `allowed_roles`."""
    return _ALL[key].roles


def _role_names(user):
    """The user's role names, fetched once per user object."""
    if not hasattr(user, "_pdm_role_names"):
        user._pdm_role_names = set(user.groups.values_list("name", flat=True))
    return user._pdm_role_names


def allows(user, key):
    if not user.is_authenticated:
        return False
    return user.is_superuser or bool(_role_names(user) & set(_ALL[key].roles))


def pages_for(user):
    return [feature for feature in PAGES if allows(user, feature.key)]


def actions_for(user):
    return [feature for feature in ACTIONS if allows(user, feature.key)]


def access_flags(user):
    """{feature key: True/False} for templates, e.g. {% if access.households %}."""
    return {key: allows(user, key) for key in _ALL}


# One line per role, shown on the user's home page under "Your access".
ROLE_SUMMARIES = {
    r.HOUSEHOLD: "You can see your own household's PDM record and loan, and use USSD with your own number. No one else's.",
    r.GROUP_EXECUTIVE: "You apply for loans on behalf of verified members of your enterprise group.",
    r.LC1_CHAIRPERSON: "You confirm whether households really live in your village.",
    r.PARISH_CHIEF: "You profile households in your parish and follow up their progress.",
    r.PDC: "You oversee PDM in your parish: verification, loans and repayment.",
    r.SACCO_OFFICIAL: "You run the PDM SACCO: eligibility, appraisal, decisions, payouts and repayments.",
    r.SUBCOUNTY_OFFICIAL: "You register enterprise groups and supervise the parishes in your sub-county.",
    r.DISTRICT_OFFICIAL: "You confirm fund releases and supervise PDM across your district.",
    r.NATIONAL_OFFICIAL: "You release the Parish Revolving Fund and follow PDM nationally.",
    r.AUDITOR: "You can read every record and the full audit trail. You cannot change anything.",
}


def summary_for(user):
    if user.is_superuser:
        return "System administrator: full access."
    return ROLE_SUMMARIES.get(user.role, "No role assigned yet. Ask the system administrator.")
