"""Repayment schedule for a Parish Revolving Fund loan.

Interest is 6% a year, charged flat on the amount paid out for the whole
term, and shared equally across the monthly instalments. Households can
check a flat schedule with simple arithmetic. Amounts are whole shillings;
the last instalment takes any rounding difference.
"""

import calendar
import datetime
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from .models import ANNUAL_INTEREST_RATE


@dataclass
class Instalment:
    number: int
    due_date: datetime.date
    principal: int
    interest: int
    balance_after: int  # principal still owed after this instalment

    @property
    def amount(self):
        return self.principal + self.interest


def add_months(day, months):
    """The same day `months` later, or the last day of that month if it is shorter."""
    month_index = day.month - 1 + months
    year, month = day.year + month_index // 12, month_index % 12 + 1
    return day.replace(year=year, month=month, day=min(day.day, calendar.monthrange(year, month)[1]))


def total_interest(principal, term_months, rate=ANNUAL_INTEREST_RATE):
    """Flat interest for the whole term, in whole shillings."""
    interest = Decimal(principal) * Decimal(rate) * term_months / 12
    return int(interest.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def build_schedule(principal, term_months, start_date, rate=ANNUAL_INTEREST_RATE):
    """Monthly instalments, the first due one month after `start_date`."""
    interest = total_interest(principal, term_months, rate)
    principal_each, interest_each = principal // term_months, interest // term_months
    instalments, balance = [], principal
    for number in range(1, term_months + 1):
        last = number == term_months
        part_principal = balance if last else principal_each
        part_interest = interest - interest_each * (term_months - 1) if last else interest_each
        balance -= part_principal
        instalments.append(
            Instalment(number, add_months(start_date, number), part_principal, part_interest, balance)
        )
    return instalments
