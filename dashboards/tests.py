"""Tests for the dashboards (figures scoped to each level) and the auditor's audit log."""

from auditlog.models import LogEntry
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from loans.models import LoanApplication
from registry.models import AdminUnit, Household

from . import queries


def seed():
    call_command("seed_demo", verbosity=0, stdout=open("/dev/null", "w"))


class DashboardQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def user(self, username):
        return User.objects.get(username=username)

    def test_national_sees_every_household_and_districts(self):
        summary = queries.summary(self.user("national"))
        self.assertEqual(summary["households"]["total"], Household.objects.count())
        self.assertEqual([row["unit"].name for row in queries.breakdown(self.user("national"))], ["Mukono", "Wakiso"])

    def test_each_level_breaks_down_one_level_down(self):
        self.assertEqual([r["unit"].name for r in queries.breakdown(self.user("district"))], ["Goma"])
        self.assertEqual(
            [r["unit"].name for r in queries.breakdown(self.user("subcounty"))], ["Nantabulirwa", "Seeta"]
        )
        self.assertEqual(
            [r["unit"].name for r in queries.breakdown(self.user("parishchief"))], ["Bajjo", "Kitega", "Seeta Central"]
        )

    def test_parish_figures_leave_out_other_parishes(self):
        seeta = AdminUnit.objects.get(name="Seeta")
        summary = queries.summary(self.user("parishchief"))
        self.assertEqual(
            summary["households"]["total"], Household.objects.filter(village__parent=seeta).count()
        )
        self.assertEqual(summary["saccos"], 1)
        self.assertLess(summary["households"]["total"], Household.objects.count())

    def test_money_adds_up(self):
        money = queries.summary(self.user("national"))["money"]
        paid_out = LoanApplication.objects.exclude(disbursement=None)
        self.assertEqual(money["disbursed"], sum(loan.disbursement.amount for loan in paid_out))
        self.assertEqual(money["repaid"], sum(loan.total_repaid for loan in paid_out))
        self.assertGreater(money["arrears"], 0)  # the seed has a loan in arrears and a default
        self.assertTrue(0 < money["portfolio_at_risk"] <= 100)

    def test_breakdown_rows_add_up_to_the_summary(self):
        user = self.user("subcounty")
        rows, summary = queries.breakdown(user), queries.summary(user)
        self.assertEqual(sum(r["households"] for r in rows), summary["households"]["total"])
        self.assertEqual(sum(r["disbursed"] for r in rows), summary["money"]["disbursed"])

    def test_loan_status_counts_cover_every_loan(self):
        summary = queries.summary(self.user("national"))
        self.assertEqual(sum(count for _, count in summary["loans_by_status"]), LoanApplication.objects.count())


class DashboardPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.client.defaults["HTTP_HOST"] = "localhost"

    def get(self, username):
        self.client.force_login(User.objects.get(username=username))
        return self.client.get(reverse("dashboard"))

    def test_officials_from_parish_to_national_see_the_dashboard(self):
        for username in ("parishchief", "pdc", "sacco", "subcounty", "district", "national", "auditor"):
            response = self.get(username)
            self.assertEqual(response.status_code, 200, username)
            self.assertContains(response, "statusChart")
            self.assertContains(response, 'id="chart-data"')

    def test_village_and_group_roles_cannot_open_it(self):
        for username in ("household", "lc1", "groupexec"):
            self.assertEqual(self.get(username).status_code, 403, username)

    def test_logged_out_users_are_sent_to_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_names_the_area(self):
        self.assertContains(self.get("subcounty"), "Goma")
        self.assertContains(self.get("national"), "Uganda (all districts)")

    def test_parish_dashboard_does_not_list_other_parishes(self):
        self.assertNotContains(self.get("parishchief"), "Nantabulirwa")


class AuditLogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.client.defaults["HTTP_HOST"] = "localhost"

    def login(self, username):
        self.client.force_login(User.objects.get(username=username))

    def test_auditor_sees_the_log(self):
        self.login("auditor")
        response = self.client.get(reverse("audit_log"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["entries"])
        self.assertContains(self.client.get(reverse("audit_log"), {"q": "Grace"}), "Grace Nakato")

    def test_other_roles_cannot_open_the_log(self):
        for username in ("national", "district", "sacco", "parishchief", "household"):
            self.login(username)
            self.assertEqual(self.client.get(reverse("audit_log")).status_code, 403, username)

    def test_log_is_read_only(self):
        self.login("auditor")
        self.assertEqual(self.client.post(reverse("audit_log")).status_code, 405)

    def test_filters_narrow_the_entries(self):
        self.login("auditor")
        response = self.client.get(reverse("audit_log"), {"q": "Henry Mubiru"})
        self.assertTrue(response.context["entries"])
        self.assertTrue(all("Henry Mubiru" in e.object_repr for e in response.context["entries"]))
        response = self.client.get(reverse("audit_log"), {"actor": "sacco"})
        self.assertTrue(all(e.actor.username == "sacco" for e in response.context["entries"]))

    def test_a_status_change_shows_who_made_it(self):
        chair = User.objects.get(username="saccochair")
        self.client.force_login(chair)
        loan = LoanApplication.objects.get(household__nin="CF85001234ABCD")
        self.client.post(reverse("loans:loan_decide", args=[loan.pk]), {"decision": "approve"})
        entry = LogEntry.objects.get_for_object(loan).filter(action=LogEntry.Action.UPDATE).latest("timestamp")
        self.assertEqual(entry.actor, chair)
        self.login("auditor")
        self.assertContains(self.client.get(reverse("audit_log"), {"q": "Grace"}), "appraised → approved")

    def test_csv_download(self):
        self.login("auditor")
        response = self.client.get(reverse("audit_log"), {"format": "csv", "q": "Grace"})
        self.assertEqual(response["Content-Type"], "text/csv")
        lines = response.content.decode().splitlines()
        self.assertEqual(lines[0], "When,Who,Action,Record type,Record,Changes")
        self.assertTrue(all("Grace" in line for line in lines[1:]))


class QuarterlyReportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.client.defaults["HTTP_HOST"] = "localhost"

    def test_quarter_bounds(self):
        from .reports import Quarter

        q = Quarter(2026, 4)
        self.assertEqual((q.start.isoformat(), q.end.isoformat()), ("2026-10-01", "2026-12-31"))
        self.assertEqual(str(q.previous()), "2026-Q3")
        self.assertEqual(str(Quarter(2026, 1).previous()), "2025-Q4")
        self.assertEqual(Quarter.parse("2026-q2").start.isoformat(), "2026-04-01")
        self.assertIsNone(Quarter.parse("rubbish"))

    def test_report_counts_this_quarters_events(self):
        from .reports import current_quarter, quarterly_figures

        figures = quarterly_figures(User.objects.get(username="national"), current_quarter())
        self.assertGreaterEqual(figures["complaints_received"], 1)
        self.assertGreaterEqual(figures["complaints_bribery"], 1)
        self.assertGreater(figures["position"]["outstanding"], 0)

    def test_report_is_scoped_to_the_area(self):
        from .reports import current_quarter, quarterly_figures

        district = quarterly_figures(User.objects.get(username="district"), current_quarter())
        national = quarterly_figures(User.objects.get(username="national"), current_quarter())
        self.assertLess(district["position"]["disbursed"], national["position"]["disbursed"])  # Wakiso excluded

    def test_page_opens_for_reporting_roles_only(self):
        for username, expected in (("district", 200), ("national", 200), ("auditor", 200), ("subcounty", 200),
                                   ("parishchief", 403), ("sacco", 403), ("household", 403)):
            self.client.force_login(User.objects.get(username=username))
            self.assertEqual(self.client.get(reverse("quarterly_report")).status_code, expected, username)

    def test_choosing_a_quarter(self):
        self.client.force_login(User.objects.get(username="national"))
        response = self.client.get(reverse("quarterly_report"), {"q": "2025-Q3"})
        self.assertContains(response, "Quarter 3, 2025")


class CsvExportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def setUp(self):
        self.client.defaults["HTTP_HOST"] = "localhost"

    def csv(self, username, url_name, **params):
        self.client.force_login(User.objects.get(username=username))
        response = self.client.get(reverse(url_name), {"format": "csv", **params})
        self.assertEqual(response["Content-Type"], "text/csv")
        return response.content.decode().splitlines()

    def test_household_export_is_scoped(self):
        lines = self.csv("parishchief", "registry:household_list")
        self.assertTrue(lines[0].startswith("NIN,Head of household"))
        self.assertTrue(any("Grace Nakato" in line for line in lines))
        self.assertFalse(any("Annet Nakiyimba" in line for line in lines))  # another parish

    def test_export_keeps_the_filters(self):
        lines = self.csv("national", "loans:loan_list", status="defaulted")
        self.assertEqual(len(lines), 2)  # header + Joyce
        self.assertIn("Joyce Nalwoga", lines[1])

    def test_arrears_and_complaints_exports(self):
        self.assertTrue(any("Henry Mubiru" in line for line in self.csv("subcounty", "loans:arrears_list")))
        self.assertTrue(any("PDM-" in line for line in self.csv("subcounty", "feedback:complaint_list")))

    def test_export_still_needs_the_role(self):
        self.client.force_login(User.objects.get(username="district"))
        self.assertEqual(self.client.get(reverse("registry:household_list"), {"format": "csv"}).status_code, 403)
