# 7. Test cases

*Phase 3 · Correctness and testing (6 marks)* · **Owner:** ______________ (run the tests again and fill in the date and your name) · **Reviewed by:** ______________

The exam asks for at least 8 documented cases: 5 positive, 2 validation or error, and 1 access control. These 13 are each backed by an automated test (named in the Evidence column) and, where shown, a screenshot from the live rehearsal. The full suite has **291 automated tests**, run on every push by GitHub Actions.

**Last run:** 25 Nov 2026, all 13 below passed (`python manage.py test <test names> -v 2`). Re-run before submission and update this line.

| ID | Type | Case | Steps (role) | Expected result | Actual result | Evidence | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TC01 | Positive | Citizen checks eligibility | Signed out → `/eligibility/` → answer *yes* to all four | "You are likely to be eligible", next steps, nothing saved | As expected; household count unchanged | `EligibilityTests.test_public_page_needs_no_sign_in_and_stores_nothing`; screenshot 26 | Pass |
| TC02 | Positive | Whole journey, register to oversight | Ten roles in order (Parish Chief → … → auditor) | Each stage succeeds; SMS at each step; audit log names each official | As expected | `CustomerJourneyTest.test_the_whole_journey` | Pass |
| TC03 | Positive | Group executive applies and submits | `groupexec` → New application → Submit | Loan status *Submitted* | As expected | `LoanApplicationPageTests.test_group_executive_submits_a_draft`; screenshot 08 | Pass |
| TC04 | Positive | Approved loan is paid out within funds | `saccochair` → Record disbursement | Status *Disbursed*; SACCO total updated | As expected | `DisbursementTests.test_sacco_official_records_a_disbursement`; screenshot 11 | Pass |
| TC05 | Positive | Repayment with a receipt | `saccochair` → Record repayment 53,000 | Status *Repaying*; instalment 1 paid; RCPT receipt; SMS | As expected | `RepaymentTests.test_first_repayment_moves_the_loan_to_repaying`; screenshot 13 | Pass |
| TC06 | Positive | Household uses USSD in Luganda | Household phone → `0` → `1`, `2`, `3`… | Every reply in Luganda; choice remembered | As expected | `LugandaTests.test_every_path_answers_in_luganda`; screenshot 15 | Pass |
| TC07 | Positive | Upheld appeal returns the loan to the SACCO | `sylvia` appeals → `subcounty` refers back | Appeal *Upheld*; loan *Appraised*; SMS; maker-checker still applies | As expected | `AppealTests.test_upheld_appeal_sends_the_loan_back_to_the_sacco`; screenshots 29–30 | Pass |
| TC08 | Validation | Loan above the ceiling | `groupexec` applies for UGX 1,500,000 | Refused: "cannot be more than UGX 1,000,000" | As expected; no loan saved | `LoanApplicationPageTests.test_loan_above_the_ceiling_is_refused` | Pass |
| TC09 | Validation | Rejection without a reason | `saccochair` rejects with a blank reason | Refused: "Give the reason for rejecting"; status unchanged | As expected | `DecisionTests.test_rejection_without_a_reason_is_refused` | Pass |
| TC10 | Validation | Phone number already used | `parishchief` registers a household with Grace's number | Refused, naming the household that has it | As expected | `HouseholdPhoneTests.test_a_number_used_by_another_household_is_refused` | Pass |
| TC11 | Access control | Appraiser tries to decide (maker-checker) | `sacco` appraises, then posts *approve* | Refused: "Another SACCO official must decide"; status unchanged | As expected | `MakerCheckerTests.test_appraiser_posting_a_decision_is_refused_with_a_message`; screenshot 10 | Pass |
| TC12 | Access control | Official opens another parish's records | `parishchief` (Seeta) opens a Nantabulirwa household, group, SACCO, loan, complaint | 403 or 404 for each | As expected | `CrossParishTests.test_reading_records_in_another_parish_is_refused` | Pass |
| TC13 | Access control | Household dials as a neighbour | `household` posts another household's number to USSD | Refused: "only dial with your own number"; no data shown | As expected | `SimulatorTests.test_household_cannot_dial_as_a_neighbour` | Pass |

## How to re-run

```bash
python manage.py test   # all 291 tests
```

Run only these 13 cases by passing their names to `python manage.py test` with `-v 2`, for example `python manage.py test loans.tests.MakerCheckerTests -v 2`.
