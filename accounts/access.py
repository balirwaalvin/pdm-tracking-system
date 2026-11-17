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
    Feature("ussd_simulator", "USSD", "ussd:simulator",
            (r.LC1_CHAIRPERSON, r.PARISH_CHIEF, r.SUBCOUNTY_OFFICIAL),
            "Try the household USSD menu, to help residents who ask."),
    Feature("audit_log", "Audit log", "audit_log", (r.AUDITOR,),
            "Every change to every record, read-only, with CSV download."),
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
    Feature("record_release", "Record fund releases", "", (r.NATIONAL_OFFICIAL,),
            "Record Parish Revolving Fund transfers to eligible SACCOs."),
    Feature("confirm_release", "Confirm fund releases", "", (r.DISTRICT_OFFICIAL,),
            "Confirm that released funds reached the SACCO's account."),
]

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
