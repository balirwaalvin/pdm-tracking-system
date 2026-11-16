"""Build a sample parish and one user for every PDM role.

Usage:
    python manage.py seed_demo            # create or update the demo data
    python manage.py seed_demo --password secret123

All data is sample data for demonstrations. Running the command again
updates the same records instead of making duplicates.
"""

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts import roles
from accounts.models import User
from django.utils import timezone

import datetime

from loans import workflow
from loans.models import Appraisal, Disbursement, LoanApplication, Repayment
from registry.models import AdminUnit, EnterpriseGroup, Household
from saccos.models import FundRelease, Sacco, SaccoChecklistItem

Level = AdminUnit.Level

# district -> sub-county -> parish -> villages
UNITS = {
    "Mukono": {
        "Goma": {
            "Seeta": ["Seeta Central", "Kitega", "Bajjo"],
            "Nantabulirwa": ["Nantabulirwa A", "Nantabulirwa B"],
        },
    },
}

# username, first name, last name, role, unit name (None = national), phone
DEMO_USERS = [
    ("household", "Grace", "Nakato", roles.HOUSEHOLD, "Seeta Central", "256700000001"),
    ("groupexec", "Peter", "Ssali", roles.GROUP_EXECUTIVE, "Seeta", "256700000002"),
    ("lc1", "Joseph", "Mukasa", roles.LC1_CHAIRPERSON, "Seeta Central", "256700000003"),
    ("parishchief", "Sarah", "Namubiru", roles.PARISH_CHIEF, "Seeta", "256700000004"),
    ("pdc", "Moses", "Kato", roles.PDC, "Seeta", "256700000005"),
    ("sacco", "Ruth", "Nabirye", roles.SACCO_OFFICIAL, "Seeta", "256700000006"),
    ("subcounty", "David", "Ouma", roles.SUBCOUNTY_OFFICIAL, "Goma", "256700000007"),
    ("district", "Agnes", "Akello", roles.DISTRICT_OFFICIAL, "Mukono", "256700000008"),
    ("national", "Samuel", "Okello", roles.NATIONAL_OFFICIAL, None, "256700000009"),
    ("auditor", "Esther", "Namata", roles.AUDITOR, None, "256700000010"),
]


# name, enterprise, parish, registration number
GROUPS = [
    ("Seeta Poultry Farmers", EnterpriseGroup.Enterprise.POULTRY, "Seeta", "GOMA/EG/001"),
    ("Kitega Piggery Group", EnterpriseGroup.Enterprise.PIGGERY, "Seeta", "GOMA/EG/002"),
    ("Nantabulirwa Coffee Growers", EnterpriseGroup.Enterprise.COFFEE, "Nantabulirwa", "GOMA/EG/003"),
]

# head, NIN, phone, sex, age group, disability, size, wealth rank, village, group, verified?
HOUSEHOLDS = [
    ("Grace Nakato", "CF85001234ABCD", "256700000001", "F", "adult", False, 6, "very_poor", "Seeta Central", "Seeta Poultry Farmers", True),
    ("Isaac Mugisha", "CM92004567EFGH", "256700000011", "M", "youth", False, 3, "poor", "Seeta Central", "Seeta Poultry Farmers", True),
    ("Florence Atim", "CF70007890IJKL", "256700000012", "F", "older", True, 5, "very_poor", "Seeta Central", "Seeta Poultry Farmers", False),
    ("John Ssemwogerere", "CM88001122MNOP", "256700000013", "M", "adult", False, 7, "poor", "Kitega", "Kitega Piggery Group", False),
    ("Harriet Nansubuga", "CF95003344QRST", "256700000014", "F", "youth", False, 2, "poor", "Kitega", "Kitega Piggery Group", False),
    ("Robert Okot", "CM79005566UVWX", "256700000015", "M", "adult", True, 8, "very_poor", "Bajjo", "Kitega Piggery Group", False),
    ("Betty Namuddu", "CF83007788YZAB", "256700000016", "F", "adult", False, 4, "middle", "Bajjo", None, False),
    ("Paul Kizza", "CM90009900CDEF", "256700000017", "M", "youth", False, 3, "poor", "Nantabulirwa A", "Nantabulirwa Coffee Growers", False),
    ("Annet Nakiyimba", "CF76001357GHIJ", "256700000018", "F", "older", False, 6, "very_poor", "Nantabulirwa B", "Nantabulirwa Coffee Growers", False),
    ("Moses Waiswa", "CM86002468KLMN", "256700000019", "M", "adult", False, 5, "poor", "Kitega", "Kitega Piggery Group", True),
    ("Sylvia Nambi", "CF91003579OPQR", "256700000020", "F", "youth", False, 4, "poor", "Seeta Central", "Seeta Poultry Farmers", True),
    ("Ronald Lubega", "CM84004680STUV", "256700000021", "M", "adult", True, 6, "very_poor", "Bajjo", "Kitega Piggery Group", True),
    ("Joyce Nalwoga", "CF80005791WXYZ", "256700000022", "F", "adult", False, 5, "poor", "Kitega", "Kitega Piggery Group", True),
    ("Henry Mubiru", "CM93006802ABCE", "256700000023", "M", "youth", False, 3, "poor", "Bajjo", "Kitega Piggery Group", True),
]


class Command(BaseCommand):
    help = "Create a sample parish and one demo user for each of the ten PDM roles."

    def add_arguments(self, parser):
        parser.add_argument("--password", default="pdm12345", help="Password for every demo user.")

    @transaction.atomic
    def handle(self, *args, **options):
        units = self.create_units()
        self.create_users(units, options["password"])
        self.create_groups_and_households(units)
        self.create_saccos(units)
        self.create_loans()
        self.stdout.write(self.style.SUCCESS("Demo data ready."))

    def create_units(self):
        units = {}
        for district_name, subcounties in UNITS.items():
            district, _ = AdminUnit.objects.get_or_create(
                name=district_name, level=Level.DISTRICT, parent=None
            )
            units[district_name] = district
            for subcounty_name, parishes in subcounties.items():
                subcounty, _ = AdminUnit.objects.get_or_create(
                    name=subcounty_name, level=Level.SUBCOUNTY, parent=district
                )
                units[subcounty_name] = subcounty
                for parish_name, villages in parishes.items():
                    parish, _ = AdminUnit.objects.get_or_create(
                        name=parish_name, level=Level.PARISH, parent=subcounty
                    )
                    units[parish_name] = parish
                    for village_name in villages:
                        village, _ = AdminUnit.objects.get_or_create(
                            name=village_name, level=Level.VILLAGE, parent=parish
                        )
                        units[village_name] = village
        self.stdout.write(f"  {len(units)} administrative units")
        return units

    def create_users(self, units, password):
        for username, first, last, role, unit_name, phone in DEMO_USERS:
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "phone": phone,
                    "admin_unit": units[unit_name] if unit_name else None,
                },
            )
            user.set_password(password)
            user.save()
            user.groups.set([Group.objects.get(name=role)])

        admin, created = User.objects.get_or_create(
            username="admin", defaults={"is_staff": True, "is_superuser": True}
        )
        if created:
            admin.set_password(password)
            admin.save()
        self.stdout.write(f"  {len(DEMO_USERS)} role users and an admin (password: {password})")

    def create_groups_and_households(self, units):
        parish_chief = User.objects.get(username="parishchief")
        subcounty = User.objects.get(username="subcounty")
        lc1 = User.objects.get(username="lc1")
        groups = {}
        for name, enterprise, parish, reg_no in GROUPS:
            group, _ = EnterpriseGroup.objects.update_or_create(
                parish=units[parish],
                name=name,
                defaults={"enterprise": enterprise, "registration_number": reg_no, "registered_by": subcounty},
            )
            groups[name] = group

        for head, nin, phone, sex, age, disability, size, rank, village, group, verified in HOUSEHOLDS:
            defaults = {
                "head_name": head,
                "phone": phone,
                "sex": sex,
                "age_group": age,
                "has_disability": disability,
                "household_size": size,
                "wealth_rank": rank,
                "village": units[village],
                "enterprise_group": groups.get(group),
                "registered_by": parish_chief,
            }
            if verified:
                defaults.update(
                    verification=Household.Verification.VERIFIED,
                    verified_by=lc1,
                    verified_at=timezone.now(),
                    verification_note="Known to the village; lives here.",
                )
            Household.objects.update_or_create(nin=nin, defaults=defaults)
        self.stdout.write(f"  {len(GROUPS)} enterprise groups and {len(HOUSEHOLDS)} households")

    def create_saccos(self, units):
        sacco_user = User.objects.get(username="sacco")
        national = User.objects.get(username="national")
        district = User.objects.get(username="district")
        now = timezone.now()

        seeta, _ = Sacco.objects.update_or_create(
            parish=units["Seeta"],
            defaults={
                "name": "Seeta PDM SACCO",
                "registration_number": "SAMPLE/PDM/SEETA/001",
                "bank_name": "Sample Bank Uganda",
                "bank_account_number": "SAMPLE-0001",
            },
        )
        nantabulirwa, _ = Sacco.objects.update_or_create(
            parish=units["Nantabulirwa"],
            defaults={
                "name": "Nantabulirwa PDM SACCO",
                "registration_number": "SAMPLE/PDM/NANT/002",
                "bank_name": "Sample Bank Uganda",
                "bank_account_number": "SAMPLE-0002",
            },
        )
        for sacco in (seeta, nantabulirwa):
            sacco.ensure_checklist()
        # Seeta meets every requirement; Nantabulirwa still lacks its Supervisory Board.
        seeta.checklist.update(met=True, checked_by=sacco_user, checked_at=now)
        nantabulirwa.checklist.exclude(requirement="Supervisory Board in place").update(
            met=True, checked_by=sacco_user, checked_at=now
        )

        EnterpriseGroup.objects.filter(parish=units["Seeta"]).update(sacco=seeta)
        EnterpriseGroup.objects.filter(parish=units["Nantabulirwa"]).update(sacco=nantabulirwa)

        FundRelease.objects.get_or_create(
            sacco=seeta,
            financial_year="2025/26",
            defaults={
                "amount": 100_000_000,
                "release_date": datetime.date(2025, 9, 15),
                "reference": "SAMPLE-REL-0001",
                "recorded_by": national,
                "confirmed_by": district,
                "confirmed_at": now,
            },
        )
        self.stdout.write(f"  {Sacco.objects.count()} SACCOs with checklists and a fund release")

    def create_loans(self):
        groupexec = User.objects.get(username="groupexec")
        sacco_user = User.objects.get(username="sacco")
        now = timezone.now()

        grace = Household.objects.get(nin="CF85001234ABCD")
        loan, created = LoanApplication.objects.get_or_create(
            household=grace,
            enterprise="Layer chicken unit of 200 birds",
            defaults={
                "enterprise_group": grace.enterprise_group,
                "sacco": grace.enterprise_group.sacco,
                "amount": 800_000,
                "business_plan": "Buy 200 day-old layer chicks, feed and vaccines. Sell eggs to schools in Seeta. Repay monthly from egg sales.",
                "term_months": 12,
                "status": LoanApplication.Status.APPRAISED,
                "created_by": groupexec,
                "submitted_at": now,
            },
        )
        Appraisal.objects.get_or_create(
            application=loan,
            defaults={
                "viability_score": 4,
                "repayment_score": 4,
                "group_score": 5,
                "recommendation": Appraisal.Recommendation.APPROVE,
                "reasons": "Experienced in poultry; group vouches for her; nearby schools buy eggs.",
                "appraised_by": sacco_user,
            },
        )

        isaac = Household.objects.get(nin="CM92004567EFGH")
        LoanApplication.objects.get_or_create(
            household=isaac,
            enterprise="Broiler chickens, 100 birds per cycle",
            defaults={
                "enterprise_group": isaac.enterprise_group,
                "sacco": isaac.enterprise_group.sacco,
                "amount": 500_000,
                "business_plan": "Raise 100 broilers every six weeks and sell to Seeta market traders.",
                "term_months": 10,
                "status": LoanApplication.Status.SUBMITTED,
                "created_by": groupexec,
                "submitted_at": now,
            },
        )
        self.create_decided_loans(groupexec, sacco_user)
        self.stdout.write(f"  {LoanApplication.objects.count()} loan applications")

    def create_decided_loans(self, groupexec, sacco_user):
        """One loan at each later stage: approved, rejected and paid out."""
        today = timezone.localdate()
        # household NIN, enterprise, amount, term, status, days ago decided, reason, scores
        decided = [
            ("CM84004680STUV", "Two in-calf piglets and a sty", 700_000, 12, LoanApplication.Status.APPROVED, 2,
             "Strong plan and the group vouches for him.", (4, 3, 4)),
            ("CF91003579OPQR", "Mobile phone repair kiosk", 1_000_000, 6, LoanApplication.Status.REJECTED, 5,
             "Phone repair is not a PDM pillar enterprise in this parish, and six months is too short to repay UGX 1M. "
             "The group may reapply for a poultry or produce enterprise.", (2, 2, 3)),
            ("CM86002468KLMN", "Piggery: four weaners, feed and drugs", 600_000, 12, LoanApplication.Status.DISBURSED, 46,
             "Experienced pig farmer; repayment plan matches pig sales.", (4, 4, 4)),
            ("CM93006802ABCE", "Piggery: three weaners and a sty", 450_000, 9, LoanApplication.Status.DISBURSED, 81,
             "Group vouches for him; first loan, so a modest amount.", (3, 3, 4)),
            ("CF80005791WXYZ", "Pig feed milling for group members", 900_000, 12, LoanApplication.Status.DISBURSED, 141,
             "Feed is the group's biggest cost; plan is sound.", (4, 3, 4)),
        ]
        # household NIN -> repayments as (days after payout, amount, reference)
        repayments = {
            "CM86002468KLMN": [(30, 53_000, "SAMPLE-RCPT-0001")],
            "CM93006802ABCE": [(31, 52_250, "SAMPLE-RCPT-0002")],
        }
        for nin, enterprise, amount, term, status, days_ago, reason, scores in decided:
            household = Household.objects.get(nin=nin)
            decided_at = timezone.now() - datetime.timedelta(days=days_ago)
            approve = status != LoanApplication.Status.REJECTED
            loan, created = LoanApplication.objects.get_or_create(
                household=household,
                enterprise=enterprise,
                defaults={
                    "enterprise_group": household.enterprise_group,
                    "sacco": household.enterprise_group.sacco,
                    "amount": amount,
                    "business_plan": f"{enterprise}. Repay monthly from sales.",
                    "term_months": term,
                    "status": status,
                    "created_by": groupexec,
                    "submitted_at": decided_at - datetime.timedelta(days=7),
                    "decided_by": sacco_user,
                    "decided_at": decided_at,
                    "decision_reason": reason,
                },
            )
            Appraisal.objects.get_or_create(
                application=loan,
                defaults={
                    "viability_score": scores[0],
                    "repayment_score": scores[1],
                    "group_score": scores[2],
                    "recommendation": Appraisal.Recommendation.APPROVE if approve else Appraisal.Recommendation.REJECT,
                    "reasons": reason,
                    "appraised_by": sacco_user,
                },
            )
            if status == LoanApplication.Status.DISBURSED:
                Disbursement.objects.get_or_create(
                    application=loan,
                    defaults={
                        "amount": amount,
                        "disbursed_on": today - datetime.timedelta(days=days_ago - 1),
                        "method": Disbursement.Method.MOBILE,
                        "reference": f"SAMPLE-TXN-{loan.pk:04d}",
                        "recorded_by": sacco_user,
                    },
                )
                for days_after, paid, reference in repayments.get(nin, []):
                    Repayment.objects.get_or_create(
                        application=loan,
                        reference=reference,
                        defaults={
                            "amount": paid,
                            "paid_on": loan.disbursement.disbursed_on + datetime.timedelta(days=days_after),
                            "method": Repayment.Method.MOBILE,
                            "recorded_by": sacco_user,
                        },
                    )
                # Bring the status in line with the repayments (no change if already there).
                loan.refresh_from_db()
                if loan.status == LoanApplication.Status.DISBURSED and loan.repayments.exists():
                    workflow.after_repayment(loan)
                workflow.flag_default(loan)
