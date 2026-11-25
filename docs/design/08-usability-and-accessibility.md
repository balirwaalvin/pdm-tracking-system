# 8. Usability and accessibility checks

*Phase 3 · Usability (4 marks)* · **Owner:** Nalweyiso Samalie Ruth · **Reviewed by:** Ogenrwot Churchill, Okello Emmanuel (sign when checked)

## 8.1 Automated accessibility check

**Tool:** axe-core 4.10 (WCAG 2.0 and 2.1, levels A and AA), run in Chromium against 14 pages, as the user who sees each page.

| Run | Result |
| --- | --- |
| First run, 25 Nov 2026 | 12 of 14 pages clean. **Found:** the status filter on the household list and the loan list had no accessible name (*select-name*, critical). |
| Fix | Added `aria-label`s to the status filters and search boxes (commit "Label the status filters and search boxes for screen readers"). |
| Second run, 25 Nov 2026 | **14 of 14 pages: no violations.** |

Pages checked: home (signed out and signed in), sign-in, eligibility, parish pages, household list and form, loan list and loan page, dashboard, My household, USSD, complaints and audit log.

## 8.2 Manual checks

| Check | How | Result |
| --- | --- | --- |
| Consistent navigation | Same top bar and sidebar on every page; the sidebar shows only the user's own pages, and the current page is highlighted | Pass |
| Meaningful feedback | Every action shows a message (green success, red error with how to fix it); forms show errors beside the field | Pass |
| Readable content | Plain British English; short sentences; amounts as "UGX 600,000"; dates as "25 Nov 2026" | Pass |
| Responsive behaviour | Checked at phone width (Pixel 7): the sidebar becomes a menu button; tables scroll inside their card | Pass (screenshot 24) |
| Keyboard | Tab through sign-in, a loan decision and the USSD screen; a visible gold focus outline | Pass |
| Low-literacy and no-smartphone users | USSD menus are 4–6 short options; Luganda available | Pass |
| Colour | Status is shown by text as well as colour (badges have words) | Pass |

## 8.3 Known limits

- Luganda wording needs review by a native speaker.
- The charts on the dashboard have a text table beside them, but the chart canvases themselves are not described in detail for screen readers.
- No usability test with real users yet. **Group task:** run a short think-aloud test with two people (with consent, instruction 9) and record the findings here.
