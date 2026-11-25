# 2. Current and proposed process

*Phase 1 · Process modelling (8 marks)* · **Owner:** ______________ · **Reviewed by:** ______________

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
