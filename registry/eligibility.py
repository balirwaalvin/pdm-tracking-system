"""Who can get a PDM loan: a public self-check, and a checklist for a registered household.

The public self-check asks four questions and stores nothing. The household
checklist reads the household's own record and says what is done and what
to do next.
"""

from loans.forms import OPEN_STATUSES

from .models import Household

# The public self-check: (key, question, hint shown when the answer is "no")
QUESTIONS = [
    ("adult_head", "Are you the head of your household, aged 18 or over?",
     "PDM support goes to households through their head, who must be an adult."),
    ("resident", "Do you live in the parish where you would apply?",
     "You apply in the parish where you live, so your LC I chairperson can confirm it."),
    ("subsistence", "Does your household mainly grow or make things for its own use, with little to sell?",
     "PDM prioritises households working mainly for their own use (the subsistence economy)."),
    ("group", "Are you in an enterprise group, or willing to join one?",
     "PDM loans go to households through their enterprise group, so you need to belong to one."),
]

NEXT_STEPS = [
    "Visit your Parish Chief with your national ID to be profiled.",
    "Your LC I chairperson confirms that you live in the village.",
    "Join an enterprise group in your parish; the group executive applies for the loan with you.",
    "The PDM SACCO appraises the application. You can follow it by USSD or online.",
]


def screen(answers):
    """answers: {key: "yes"|"no"} -> (likely_eligible, [hints for each "no"])."""
    gaps = [hint for key, _, hint in QUESTIONS if answers.get(key) != "yes"]
    return not gaps, gaps


def household_checklist(household):
    """What a registered household has done towards a loan, and what is left. Each item: label, ok, note."""
    group = household.enterprise_group
    sacco = group.sacco if group else None
    open_loan = household.loans.filter(status__in=OPEN_STATUSES).first()
    return [
        {"label": "Profiled by the Parish Chief", "ok": True, "note": "Your household is on the PDM register."},
        {"label": "Confirmed by your LC I chairperson",
         "ok": household.verification == Household.Verification.VERIFIED,
         "note": {"verified": "Confirmed.", "pending": "Waiting for the LC I to confirm.",
                  "rejected": f"Not confirmed: {household.verification_note}"}[household.verification]},
        {"label": "In the priority group (subsistence households)",
         "ok": household.wealth_rank in (Household.WealthRank.VERY_POOR, Household.WealthRank.POOR),
         "note": f"Wealth rank: {household.get_wealth_rank_display().lower()}."},
        {"label": "Member of an enterprise group", "ok": group is not None,
         "note": group.name if group else "Ask your Parish Chief which groups are open in your parish."},
        {"label": "Group linked to an eligible PDM SACCO", "ok": bool(sacco and sacco.is_eligible),
         "note": sacco.name if sacco else "Your group is not yet linked to a SACCO."},
        {"label": "No other open loan", "ok": open_loan is None,
         "note": "None." if open_loan is None else f"You have a loan of UGX {open_loan.amount:,} ({open_loan.get_status_display().lower()})."},
    ]
