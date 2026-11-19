# Walkthrough and security check (Mon 23 Nov 2026)

What was checked, what was found and how it was fixed. The checks are automated tests, so they run again on every push.

## Walkthrough as every role

- A crawler signed in as each of the 11 demo accounts (all ten roles, plus the second SACCO official), opened every page in the role's menu and every link on those pages: about 450 pages. It found no server errors and no links that lead a role to a page it cannot open.
- `dashboards/test_journey.py` drives the whole ten-stage customer journey through the real pages, signed in as the right role at each step: register, verify, group, apply, appraise, decide (maker-checker) and pay out, repay, USSD and SMS, complaint and success story, dashboard and audit trail.
- Screens were checked in a browser at desktop and phone width.

## Security checks (`accounts/test_security_sweep.py`)

| Check | Result |
| --- | --- |
| Signed out: every non-public URL in the project (found automatically) sends you to sign in | Passes after fix 1 |
| Cross-parish: Seeta officials cannot open or change Nantabulirwa or Wakiso households, groups, SACCOs, loans or complaints | Passes |
| Lists and CSV exports leave out other areas | Passes |
| Wrong role: the role-by-page access matrix (`accounts/test_access.py`) and maker-checker tests | Passes |
| CSRF: forms and sign-in refuse posts without the token | Passes |
| Production settings: `manage.py check --deploy` | No issues (2 silenced on purpose, below) |

## Found and fixed

1. **Fund release page answered "not found" to signed-out users** instead of sending them to sign in, which also showed whether a SACCO number existed. It now checks sign-in first.
2. **Groups registered on the web were not linked to their parish SACCO**, so their members could never apply for a loan (only the sample data had the link). New groups are now linked automatically, with a warning if the parish has no eligible SACCO.
3. **The USSD callback was open to anyone**: posting a household's phone number returned its loan status. It is public by design (Africa's Talking must reach it), so it now requires a secret `?token=` when `USSD_CALLBACK_TOKEN` is set. It is set on Render; the in-app USSD simulator is not affected.
4. **No HTTPS redirect or HSTS in production.** Both are now on through Render settings (`SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS=3600`), and pages cannot be framed by other sites.
5. **Sign-ins flooded the audit log** as "System" records, hiding real changes. Sign-ins are kept only in their own sign-in log now.
6. **Appraisal form showed a blank "---------" score option**, and the scores were long vertical lists. The blank is gone and the 1 to 5 choices sit in a row.

## Left as they are, on purpose

- HSTS does not cover subdomains and is not preloaded: treez.tech hosts other sites, and preloading is hard to undo.
- The demo password `pdm12345` is shown on the sign-in page and in the README. Acceptable for a prototype with sample data only; a real system would issue individual passwords.
- SMS and USSD use sample phone numbers and the Africa's Talking sandbox is not connected.
