---
okf_version: '0.2'
namespace: acme_corp/users/emp_042
title: Knowledge Profile for emp_042
last_updated: '2026-11-13T01:53:51Z'
active_claims: 4
superseded_claims: 3
disputed_claims: 2
quarantined_claims: 3
---

# Knowledge Profile for emp_042

## Active Claims
- Target database: PostgreSQL 16.[^src_03fab7]
- Primary key spec: uuidv7.[^src_355a53]
- Favorite color: electric indigo.[^src_24f482]
- Lives in: Bengaluru.[^src_840b49]

## Superseded Claims
- Lives in (Historical): Mangalore.[^src_01]
- Lives in (Historical): Bengaluru.[^src_12]
- Lives in (Historical): Mangaluru.[^src_24f482]

## Disputed Claims
- Preferred db: MongoDB.[^src_survey]
- Lives in: Mumbai.[^src_68f912]

## Evidence & Citations
[^src_01]: sources/session_01.txt "I am based out of Mangalore" (trust_tier=4)
[^src_03fab7]: sources/session_20261112_204932_src_03fab7.txt "Payment service migration will switch from MongoDB to PostgreSQL 16." (trust_tier=3)
[^src_12]: sources/session_12.txt "now live in Bengaluru" (trust_tier=4)
[^src_24f482]: sources/session_20261113_015157_src_24f482.txt "My favorite color is electric indigo and I live in Mangaluru." (trust_tier=4)
[^src_355a53]: sources/session_20261112_204932_src_355a53.txt "All primary keys in payment tables must use uuidv7." (trust_tier=3)
[^src_68f912]: sources/session_20261113_015243_src_68f912.txt "Employee 042 currently lives in Mumbai." (trust_tier=1)
[^src_840b49]: sources/session_20261113_015223_src_840b49.txt "I moved to Bengaluru this week." (trust_tier=4)
[^src_survey]: sources/infra_survey_doc.txt "emp_042 indicated preferred DB is MongoDB" (trust_tier=2)
