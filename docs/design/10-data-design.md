# 10. Data design

*Phase 4 · Data design (4 marks)* · **Owner:** ______________ · **Reviewed by:** ______________

## 10.1 Entity relationship diagram

```mermaid
erDiagram
  ADMIN_UNIT ||--o{ ADMIN_UNIT : "parent of"
  ADMIN_UNIT ||--o{ USER : "area of"
  ADMIN_UNIT ||--o{ HOUSEHOLD : "village of"
  ADMIN_UNIT ||--o{ ENTERPRISE_GROUP : "parish of"
  ADMIN_UNIT ||--o| SACCO : "parish of"
  SACCO ||--o{ ENTERPRISE_GROUP : serves
  SACCO ||--o{ SACCO_CHECKLIST_ITEM : has
  SACCO ||--o{ FUND_RELEASE : receives
  ENTERPRISE_GROUP ||--o{ HOUSEHOLD : "has members"
  HOUSEHOLD |o--o| USER : "signs in as"
  HOUSEHOLD ||--o{ LOAN_APPLICATION : applies
  ENTERPRISE_GROUP ||--o{ LOAN_APPLICATION : "applies through"
  SACCO ||--o{ LOAN_APPLICATION : decides
  LOAN_APPLICATION ||--o| APPRAISAL : "scored by"
  LOAN_APPLICATION ||--o| DISBURSEMENT : "paid by"
  LOAN_APPLICATION ||--o{ REPAYMENT : "repaid by"
  LOAN_APPLICATION ||--o| APPEAL : "appealed by"
  LOAN_APPLICATION ||--o{ SMS_MESSAGE : "alerts"
  HOUSEHOLD ||--o{ COMPLAINT : raises
  COMPLAINT ||--o{ COMPLAINT_RESPONSE : "answered by"
  HOUSEHOLD ||--o{ SUCCESS_STORY : "subject of"
  USER ||--o{ SIGN_IN_EVENT : "attempts"

  ADMIN_UNIT {
    int id PK
    string name
    string level "district|subcounty|parish|village"
    int parent_id FK
  }
  USER {
    int id PK
    string username UK
    string phone
    int admin_unit_id FK
  }
  HOUSEHOLD {
    int id PK
    string nin UK "14 chars"
    string head_name
    string phone UK
    string wealth_rank
    string verification
    int village_id FK
    int enterprise_group_id FK
  }
  ENTERPRISE_GROUP {
    int id PK
    string name
    int parish_id FK
    int sacco_id FK
  }
  SACCO {
    int id PK
    string name
    int parish_id FK "one per parish"
  }
  FUND_RELEASE {
    int id PK
    int amount
    string financial_year
    int confirmed_by FK
  }
  LOAN_APPLICATION {
    int id PK
    int amount
    int term_months
    string status
    int household_id FK
    int sacco_id FK
    int decided_by FK
  }
  APPRAISAL {
    int id PK
    int viability
    int repayment
    int group_score
    string recommendation
    int appraised_by FK
  }
  DISBURSEMENT {
    int id PK
    int amount
    date disbursed_on
    string method
    string reference
  }
  REPAYMENT {
    int id PK
    int amount
    date paid_on
    string reference
    string receipt "RCPT-xxxxxx"
  }
  APPEAL {
    int id PK
    string grounds
    string status
    int decided_by FK
  }
  COMPLAINT {
    int id PK
    string category
    string status
    string level
    datetime awaiting_since
  }
  SUCCESS_STORY {
    int id PK
    bool consent_given
    bool show_name
    string status
    int checked_by FK
  }
```

Every table also has an **audit log** (django-auditlog): who changed which field, from what, to what, and when.

## 10.2 Identifiers

| Entity | Identifier shown to people |
| --- | --- |
| Household | National ID number (NIN), unique |
| Complaint | `PDM-000123` (digits only, easy on a keypad) |
| Appeal | `APL-000123` |
| Repayment receipt | `RCPT-000123` |
| Disbursement | Mobile money or bank reference |

## 10.3 Validation rules

| Field | Rule | Where enforced |
| --- | --- | --- |
| NIN | 14 letters or digits, stored in capitals, unique | Model validator + database unique constraint |
| Phone | Uganda format, unique per household | Form + database |
| Loan amount | UGX 10,000 to 1,000,000 | Form + model |
| Term | 3–24 months | Form |
| One open loan | A household may have only one loan not yet closed | Form |
| Verification | Rejection needs a note | Form + view |
| Decision | Rejection needs a reason; appraiser cannot decide | `workflow.move()` |
| Disbursement | Not above approved amount or SACCO's confirmed funds | Form |
| Appeal | Within 30 days of rejection; grounds of at least 10 characters; decision note required | `feedback/appeals.py` |
| Story | Consent recorded before PDC check | Form + view |

## 10.4 Retention and data minimisation

- **Collected only what PDM needs:** no photos, no exact GPS, no bank account details, no income figures; age as a band, not a date of birth.
- **Public pages** show only totals; stories show the first name and village unless the household agreed to be named.
- **Records are never deleted** by users (`on_delete=PROTECT` on loans and households) so the audit trail stays complete.
- **Retention (proposal for a real system):** loan records 7 years after closure, complaints 3 years, sign-in log 1 year **[verify against the Data Protection and Privacy Act 2019 and PFMA rules]**.
- **Prototype:** all data is fictitious and can be wiped and reloaded with *Reset demo data*.
