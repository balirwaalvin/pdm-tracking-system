# 2. Current and proposed process

*Phase 1 · Process modelling (8 marks)* · **Owner:** Kaitesi Lillian · **Reviewed by:** Balirwa Alvin Daniel, Ssuubi Stephen, Okello Emmanuel (sign when checked)

Flowcharts with swimlanes (one lane per role). They render on GitHub; for the report, redraw them in a BPMN 2.0 tool (for example draw.io or Camunda Modeler) if the assessor prefers BPMN notation.

## 2.1 Current process (paper based, as described in the guidelines and to be confirmed by interviews)

```mermaid
flowchart LR
  subgraph HH[Household]
    A([Start: wants a loan]) --> B[Visits the parish office]
    K[Waits; travels to ask about the file]
    R([End: told the outcome, often verbally])
  end
  subgraph PC[Parish Chief]
    C[Fills a paper profile form]
  end
  subgraph LC[LC I Chairperson]
    D{Lives in the village?}
  end
  subgraph GE[Group executive]
    E[Fills a paper application]
  end
  subgraph SA[PDM SACCO]
    F[File waits in a queue]
    G{Appraise and decide}
    H[Pays out]
  end
  B --> C --> D
  D -- yes --> E --> F --> G
  D -- no, no written reason --> R
  G -- approve --> H --> R
  G -- reject, reason not recorded --> R
  F -. no status visible .-> K -.-> F
```

**Exceptions:** files lost or incomplete; household cannot be reached; a complaint is raised verbally with no record; a refusal cannot be appealed because no reason was written.

### Measurable bottleneck

| Measure | Current (baseline) | How it is measured |
| --- | --- | --- |
| **Time from submission to SACCO decision** | Estimated **3 to 6 weeks** **[assumption: confirm in interviews]** | Days between application date and decision date in SACCO files |
| Household trips to ask about status | Estimated **2 to 4 per application** **[assumption]** | Interviews with households |
| Refusals with a written reason | Estimated **under 50%** **[assumption]** | Sample of SACCO files |
| Complaints with a reference and an answer | Not recorded **[assumption]** | Parish complaint books |

The bottleneck is **the SACCO queue (F) combined with no visible status**: files wait without anyone above knowing, and households must travel to find out.

## 2.2 Proposed process (the prototype)

```mermaid
flowchart LR
  subgraph HH[Household]
    A([Start]) --> A1[Checks eligibility online, free]
    S1[Gets an SMS at each step; checks status by USSD]
    AP[Appeals a rejection within 30 days]
    Z([End: loan repaid and closed])
  end
  subgraph PC[Parish Chief]
    B[Profiles the household; NIN checked against a mock ID register]
  end
  subgraph LC[LC I Chairperson]
    C{Confirm household?}
  end
  subgraph GE[Group executive]
    D[Applies online for a verified member; submits]
  end
  subgraph SA[PDM SACCO]
    E[Official 1 appraises: scores and reasons]
    F{Official 2 decides: maker-checker}
    G[Records payout and repayments; receipts]
  end
  subgraph SC[Sub-county]
    H{Decides appeals and escalated complaints}
  end
  subgraph SYS[System]
    T[Schedule at 6%; flags arrears and 90-day default; escalates complaints after 7 days]
  end
  A1 --> B --> C
  C -- yes --> D --> E --> F
  C -- no, reason required --> S1
  F -- approve --> G --> T --> Z
  F -- reject, reason required --> S1 --> AP --> H
  H -- refer back --> F
  H -- dismiss, reason sent --> S1
```

## 2.3 What changes

| Problem in the current process | Change in the proposed process | Feature |
| --- | --- | --- |
| No visible status | Status on the web, by USSD and by SMS at each step | My household, USSD, SMS alerts |
| Refusals without reasons | A reason is required for every rejection | Decision form, LC I verification |
| One person appraises and decides | Maker-checker: a second official decides | Workflow rule |
| No way to challenge a refusal | Appeal to the sub-county within 30 days | Appeals |
| Complaints lost | Reference numbers; escalation after 7 days; bribery reports skip the parish | Complaints |
| Late paper reports | Live dashboards and quarterly reports | Dashboard, Reports |

**Target:** submission-to-decision time **under 7 days**, with every refusal carrying a reason (see section 3).

## 2.4 System flowchart: one application from start to finish

Standard flowchart symbols: rounded ends are start and finish points, diamonds are decisions, and pink boxes are refusals or problems. Every rule shown is enforced by the prototype (for example, a rejection needs a reason, the official who appraises cannot decide, and a payout cannot exceed the SACCO's confirmed funds). Image: [diagrams/D6-system-flowchart.png](diagrams/D6-system-flowchart.png).

```mermaid
flowchart TD
  A([Start: household hears about PDM]) --> B[/Checks eligibility online, free, nothing saved/]
  B --> C[Parish Chief profiles the household: NIN, village, wealth rank]
  C --> D{NIN valid, unique and<br/>found in the ID register?}
  D -- No --> D1[Correct the details or<br/>refer to NIRA] --> C
  D -- Yes --> E{LC I confirms the household<br/>lives in the village?}
  E -- No, with a reason --> E1([Rejected: household is told why,<br/>can raise a complaint])
  E -- Yes --> F{In an enterprise group linked<br/>to an eligible SACCO?}
  F -- No --> F1[CDO registers the group and<br/>links it to the parish SACCO] --> F
  F -- Yes --> G[Group executive applies:<br/>UGX 10,000 to 1,000,000, 3 to 24 months]
  G --> H{Verified member and<br/>no other open loan?}
  H -- No --> H1([Refused by the form,<br/>with the reason shown])
  H -- Yes --> I[Submitted to the SACCO · SMS]
  I --> J[SACCO official appraises:<br/>viability, repayment, group, out of 15]
  J --> K{A second SACCO official decides<br/>maker-checker}
  K -- Reject, reason required --> L[Rejected · SMS with the reason]
  L --> M{Household appeals<br/>within 30 days?}
  M -- No --> M1([Rejection stands])
  M -- Yes --> N{Sub-county decides<br/>the appeal}
  N -- Dismiss, with a note --> M1
  N -- Uphold --> J2[Back to the SACCO for a fresh decision] --> K
  K -- Approve --> O[Approved · SMS]
  O --> P{Payout within the approved amount<br/>and the SACCO's confirmed funds?}
  P -- No --> P1[Wait for a fund release:<br/>national records, district confirms] --> P
  P -- Yes --> Q[Disbursed · repayment schedule at 6% a year · SMS]
  Q --> R[Household repays · numbered receipt · SMS]
  R --> S{Balance paid in full?}
  S -- Yes --> T([Loan closed])
  S -- No --> U{Instalment overdue?}
  U -- No --> R
  U -- Yes --> V{More than 90 days overdue?}
  V -- No --> V1[On the arrears list for the SACCO<br/>and officials above] --> R
  V -- Yes --> W[Flagged as defaulted] --> R

  classDef term fill:#0B2E6B,stroke:#0B2E6B,color:#FFFFFF
  classDef dec fill:#FFF5D1,stroke:#B88A00,color:#14213A
  classDef bad fill:#FDE6EF,stroke:#CC0A5A,color:#14213A
  classDef step fill:#FFFFFF,stroke:#5F6980,color:#14213A
  class A,T term
  class D,E,F,H,K,M,N,P,S,U,V dec
  class E1,H1,M1,L,W bad
  class B,C,D1,F1,G,I,J,J2,O,P1,Q,R,V1 step
```
