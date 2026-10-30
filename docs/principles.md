# Engineering Principles

Binding rules for anyone (human or Claude) designing, coding or reviewing this project. They exist because the first implementation drifted from the Data Vault 2.0 standard and had to be rebuilt (review R-33, lessons learned). This file is imported into `CLAUDE.md`, so it applies to every session.

**Precedence.** PRD (`docs/PRD.md`) defines *what* to build; this file defines *how* it must be built. If a requirement cannot be met without breaking a principle, stop and raise it through the change process (PRD section 8). Never resolve the conflict silently in code.

**Evidence rule.** Every principle below cites its source. A design choice not covered here must either follow a cited standard or be recorded as a deviation (section 7) with evidence. "It works" is not evidence; a reference, a measurement or a reproducible failure is.

## 1. References

| ID | Source |
| --- | --- |
| [DVA-LATE] | Data Vault Alliance, *Understanding Late Arriving Data*: https://datavaultalliance.com/news/dv/dv-tips/understanding-late-arriving-data/ |
| [SF-LATE] | Scalefree, *How to Deal With Late Arriving Data*: https://www.scalefree.com/knowledge/webinars/data-vault-friday/how-to-deal-with-late-arriving-data/ |
| [SF-INSERT] | Scalefree, *How to Implement Insert Only in Data Vault 2.0*: https://www.scalefree.com/blog/data-vault/insert-only-in-data-vault/ |
| [SF-GHOST] | Scalefree, *Implementing Data Vault 2.0 Ghost Records*: https://www.scalefree.com/scalefree-newsletter/implementing-dv2-0-ghost-records/ |
| [SF-ZERO] | Scalefree, *Implementing Data Vault 2.0 Zero Keys*: https://www.scalefree.com/scalefree-newsletter/implementing-data-vault-2-0-zero-keys/ |
| [SF-CORRUPT] | Scalefree, *Dealing with Corrupted Loads in Data Vault*: https://www.scalefree.com/knowledge/webinars/data-vault-friday/dealing-with-corrupted-loads-in-data-vault/ |
| [SF-ERROR] | Scalefree, *Defining the Error Mart in Data Vault*: https://www.scalefree.com/wissen/webinare/data-vault-friday/defining-the-error-mart-in-data-vault/ |
| [SF-GLOSSARY] | Scalefree, *Data Vault Glossary*: https://www.scalefree.com/blog/data-vault/data-vault-glossary-hub-link-satellite-business-vault-and-more/ |
| [MS-DV] | Microsoft, *Data Vault 2.0 on Azure*: https://techcommunity.microsoft.com/blog/analyticsonazure/data-vault-2-0-on-azure/3860665 |
| [MS-BL] | Microsoft, *Implementing Business Logic using Data Vault 2.0*: https://techcommunity.microsoft.com/blog/analyticsonazure/implementing-business-logic-using-data-vault-2-0-on-azure-fabric/4287170 |
| [DV4DBT-EFF] | datavault4dbt, *How to Track Effectivity*: https://www.datavault4dbt.com/documentation/v2.0/general-usage-notes/how-to-track-effectivity/ |
| [ADV-XTS] | AutomateDV, *Extended Tracking Satellites*: https://automate-dv.readthedocs.io/en/latest/tutorial/tut_xts/ |
| [ADV-MAT] | AutomateDV, *Materialisations*: https://automate-dv.readthedocs.io/en/latest/materialisations/ |
| [ADV-LOAD] | AutomateDV, *Loading* (multiple records per key in a batch, base and incremental loads): https://automate-dv.readthedocs.io/en/latest/best_practises/loading/ |
| [LINSTEDT] | D. Linstedt, M. Olschimke, *Building a Scalable Data Warehouse with Data Vault 2.0*, Morgan Kaufmann, 2015 |
| [EVAL] | Project evaluation against the standard: `docs/danh-gia-kien-truc-dv2.md` |
| R-xx | Project decision records in `docs/review.md` |

## 2. Data Vault 2.0

**DV-01 Layering.** Data flows staging → Raw Vault → Business Vault → information marts. Staging is transient and only feeds the Raw Vault. The Business Vault (including PIT and bridge tables) and the marts read only the Raw Vault and the Business Vault, never staging. *Evidence:* [SF-GHOST] (PIT is a Business Vault object built from Hub/Link and Satellites), [LINSTEDT]; violation and fix in R-33 #1.

**DV-02 Hard rules before the Raw Vault, soft rules after.** Before the Raw Vault only technical adjustments that do not change meaning are allowed: data type alignment, system columns, de-duplication of identical copies. Business checks (domain ranges, completeness, orphans, cleansing, interpretation) belong in the Business Vault or a quality layer, so rules can change without reloading raw data. Interpreting source missing codes (for example `9999`, `XX`) as null is a soft rule: staging keeps them, the Business Vault converts them (`missing_to_null`). *Evidence:* [MS-DV], [MS-BL], [SF-ERROR]; R-33 #2, R-35 #1.

**DV-03 Load all data; only technical conditions while loading the Raw Vault.** The Raw Vault aims to hold all delivered data regardless of quality. The only conditions allowed in Raw Vault loading are technical ones: the delta check against the latest version and replacing missing keys with zero keys. No business filters in Raw Vault models. A whole delivery that fails technical validation may be set aside, because the data lake/persistent staging area keeps the original. *Evidence:* [SF-ZERO], [SF-CORRUPT]; R-33 #4.

**DV-04 Load date is technical and only moves forward.** `load_date` is the time the data was inserted into the warehouse, assigned per load batch. It is never redefined as a business date and never moves backwards. Business time is carried by business attributes in Satellites (applied date); PITs and snapshots follow the business timeline. *Evidence:* [DVA-LATE], [SF-LATE], [SF-INSERT]. *Project deviation:* `load_date` is the simulated arrival time of each monthly delivery during history replay (DEV-03); it must still be forward-only.

**DV-05 Insert-only.** The Raw Vault is never updated or deleted; Satellites carry no end dates. Corrections arrive as new deliveries with a new `load_date` (FR-14). *Evidence:* [SF-INSERT].

**DV-06 Deterministic hashing, fixed for life.** Hash keys and hash diffs use one rule defined once in `dbt/dbt_project.yml`: SHA-256, upper case, trim, delimiter `||`, null placeholder `^^`. The rule never changes after data has been loaded. *Evidence:* [LINSTEDT]; PRD FR-06; unit test `dbt/tests/assert_hash_rules.sql`.

**DV-07 Entity responsibilities.** Hub: one row per business key. Link: one row per relationship. Satellite: key (`hash_key`, `load_date`), a new version only when `hash_diff` differs from the previous version. Split Satellites by rate of change and by source. *Evidence:* [LINSTEDT]; P2, R-12.

**DV-08 Track presence explicitly.** When the source carries no effectivity information and deliveries are incremental, record when keys appear with a record tracking satellite (in this project: AutomateDV `xts`). Do not infer presence from staging or from Satellites, which only store changes. Relationships that change over time are tracked with effectivity or record tracking satellites. *Evidence:* [DV4DBT-EFF], [ADV-XTS]; R-33 #1, #6.

**DV-09 PIT tables follow the standard structure.** Snapshot dates come from a snapshot table. Each Satellite gets a pointer pair (parent hash key, `load_date`). When no version exists at a snapshot, the pointer targets the Satellite's ghost record, so every join from the PIT is an equi-join. *Evidence:* [SF-GHOST]; R-33 #5.

**DV-10 Ghost records and zero keys.** Every Satellite has one ghost record: zero hash key, earliest `load_date`, `record_source = SYSTEM`, null payload. Missing business keys map to a zero key instead of dropping rows. Tests that check referential integrity exclude the zero key. Implement zero keys with the AutomateDV `null_columns` stage option, which keeps the original value in `<column>_ORIGINAL`. *Evidence:* [SF-GHOST], [SF-ZERO]; R-35 #2.

**DV-11 Business Vault is derived and rebuildable.** Computed Satellites are keyed by the parent hash key plus the load or snapshot date, carry a `record_source`, and can be rebuilt from the Raw Vault at any time. *Evidence:* [LINSTEDT], [SF-GLOSSARY].

**DV-12 Error mart and quality reporting.** Rows failing hard rules go to the error mart with a reason, so they can be fixed and reloaded. Soft-rule violations are reported without blocking the Raw Vault, computed in the Business Vault from Raw Vault data (`business_vault.quality_violation`), so a rule change only rebuilds the report. *Evidence:* [SF-ERROR], [SF-GLOSSARY]; FR-07, R-35 #3.

**DV-13 Prefer the standard package.** Use AutomateDV macros as published. Write a macro only when the published one cannot run on this platform, keep its logic identical to the published version, and register the deviation with the reason (section 7). *Evidence:* P5, R-26.

## 3. Pipeline and orchestration

**PL-01 One job per layer.** Each layer (ingest, quality, raw_vault, business_vault, then gold, export) is an independent job that picks work from the control table (`control.layer_run`, `control.period_request`) and records its own status. *Evidence:* R-32, R-33 #7.

**PL-02 Read only persisted output of the layer below.** A layer never reads mutable shared state such as transient tables overwritten by another layer. *Evidence:* three silent wrong-data bugs in phases 2–3 (R-31 #9, R-32, R-33 #1).

**PL-03 Idempotent, but do not rerun what is done.** Rerunning any layer for any period must not change row counts. Idempotency makes reruns safe; it is not a reason to rerun. Completed layers are not reprocessed unless explicitly forced. When a model change requires a rebuild, mark that layer's runs `SUPERSEDED` (`python -m ingestion.control invalidate`) instead of deleting the log or rerunning the layers below. *Evidence:* R-09, R-32, R-34; AC-02.

**PL-04 Respect chronological dependencies.** Layers whose result depends on earlier periods (Raw Vault: delta check; Business Vault: seeded running values) process periods in order. The readiness rule lives in one tested function (`ingestion.control.ready_periods`). Consecutive ready periods may be loaded as one batch (`ready_batch`), in order, never mixed with a correction delivery; each period keeps its own run record. *Evidence:* R-31 #3, R-33, R-34; [ADV-LOAD] (standard Satellite batch loading); `tests/unit/test_control.py`.

**PL-05 Fail visibly, recover automatically.** Runs hold a lease; expired leases are reclaimed. Retries are bounded; a period that keeps failing stops and is reported, never retried forever. Pools prevent two Spark jobs or two dbt runs from running at the same time. *Evidence:* stuck RUNNING rows after machine restarts (30/10/2026), R-33.

## 4. Platform rules (Spark, Delta, dbt)

Each rule comes from a measured failure in this project.

| ID | Rule | Evidence |
| --- | --- | --- |
| SP-01 | Pin Spark 3.5.5 with Delta 3.3.2; do not use Spark 3.5.7 | `CREATE OR REPLACE TABLE AS SELECT` fails with Delta 3.3.2 (R-26) |
| SP-02 | Spark SQL has no `QUALIFY`; rewrite window filters as subqueries | Spark 3.5 and 4.1 both reject it (R-26) |
| SP-03 | An incremental model that references its source several times must read a table, not a view | Planning alone took 63 s and exhausted the Thrift heap (R-30) |
| SP-04 | Never put `var()` filters inside a view; filter in the model that is rebuilt each run | A frozen period filter silently read the wrong period (R-31 #9) |
| SP-05 | Build one layer with `--indirect-selection cautious` | Default `eager` selection pulled in tests of the next layer (R-33) |
| SP-06 | Read source text files as text and split; never rely on the CSV reader for field-count validation | The CSV reader pads or truncates rows silently (R-27) |
| SP-07 | Keep Bronze values as strings; cast in staging | Type errors must stay visible to the quality gate (R-27) |
| SP-08 | Limit Spark UI history on the long-running Thrift Server | `spark-defaults.conf`, R-30 |

## 5. Engineering process

**EP-01 Check the standard before designing.** Before designing a layer or entity, read the relevant standard references and cite them in the design or the review entry. *Evidence:* R-33, lesson 1.

**EP-02 Spikes test architecture principles, not only tools.** A spike must answer "does the data flow follow the standard?" as well as "does the tool run?". *Evidence:* R-33, lesson 2.

**EP-03 Fix the model, not the symptom.** A workaround that reaches across layers usually hides a gap in the model. Close the gap in the right layer. *Evidence:* R-33, lesson 3.

**EP-04 Try small before running long.** Validate on one period, the smoke fixture (`make smoke`) or an `EXPLAIN` before running all periods or a full gate. *Evidence:* R-33, lesson 6.

**EP-05 Independent verification for business logic.** Business rules are checked against an implementation that shares no code with the pipeline (for example `tests/gates/c3/oracle.py`). *Evidence:* R-31 #5.

**EP-06 Gates are not negotiable.** Each phase ends with its gate (Plan section 6). Code of the next phase starts only after the gate passes. Criteria are never relaxed without an entry in the PRD change history. Gate results are recorded in `tests/gates/results/` and tied to a commit.

**EP-07 Change management.** Changes to FRs, ACs or the architecture go through `docs/review.md`, the PRD, the Plan and the gate tests in one change, with a PRD version bump (PRD section 8).

**EP-08 No real data in the repository.** `data/` stays ignored. Fixtures are synthetic; expected values derived from real data are computed at test time, not committed.

## 6. Language

Discussion with the project owner is in Vietnamese. This file is in English, at the owner's request.

## 7. Deviation register

Approved departures from the references, each with evidence. A new deviation needs an entry here and a review record before it is merged.

| ID | Standard | Deviation | Evidence | Record |
| --- | --- | --- | --- | --- |
| DEV-01 | DV-13: use published macros | Handwritten `spark__hub`, `spark__link`, `spark__sat` (logic copied from AutomateDV's Databricks versions) and a generated shim for the other macros | AutomateDV ships no `spark__` macros; the Databricks versions use `QUALIFY`, unsupported by open-source Spark (SP-02) | R-26, R-29 |
| DEV-02 | DV-09: PIT from Hub × snapshot table | PIT rows only for loans present in the load (from `xts_loan`), loaded incrementally; output columns follow the standard structure | The AutomateDV `pit` macro rebuilds Hub × all snapshots on every run: about 155 million rows on the full dataset | R-31, R-33 |
| DEV-03 | DV-04: `load_date` = actual insert time | `load_date` = simulated arrival time of the monthly delivery (first day of the following month) during history replay; forward-only is enforced by ordered processing (PL-04) and the Satellite delta check | Project simulation choice for replaying 2019–2026 history, not a standard definition of load time. [ADV-LOAD] supports multiple versions per Satellite batch; it does not prescribe the project's simulated timestamps. `vault_insert_by_period` [ADV-MAT] is deprecated since 0.11.0 and is not used here | R-01, R-33, R-34 source clarification |
| DEV-04 | DV-08: effectivity satellite for changing relationships | No effectivity satellite on `link_loan_servicer`; monthly servicer comes from the record tracking satellite `xts_loan_servicer` | FR-11 cut for scope (one-person project); record tracking is the documented alternative when no effectivity data exists ([DV4DBT-EFF]) | R-25, R-33 |
| DEV-05 | DV-10: zero key for missing business keys | Rows with a missing or malformed loan identifier go to the error mart instead of a zero key | The loan is the central business key; without it the row cannot be attributed to any loan. Missing seller or servicer keys still follow DV-10 | R-33 |
| DEV-06 | DV-13: use published materialisations | `dbt/macros/spark_unit_test.sql` overrides dbt-core's `unit` materialisation for the `spark` adapter; one line changed: the temporary relation is created with a non-fetching `statement` instead of `run_query` | Through the Spark Thrift Server, `CREATE TEMPORARY VIEW` returns no result set, so `run_query` fails with `'NoneType' object is not iterable` and no dbt unit test can run (reproduced 30/10/2026, dbt-core 1.12.5, dbt-spark 1.11.0). Re-check against the original when upgrading dbt-core | R-35 |

## 8. Pre-commit checklist

1. Does any Business Vault, PIT, Gold or export model read from staging or another layer's transient table? (must be no)
2. Does any Raw Vault model contain a business filter or a soft-rule check? (must be no)
3. Do rows that violate only soft rules still reach the Raw Vault? (must be yes)
4. Is every handwritten macro or non-standard structure listed in the deviation register with evidence? (must be yes)
5. Are new entities (Hub, Link, Satellite, PIT, tracking satellite) consistent with DV-07 to DV-11?
6. Does an incremental model that references its source more than once read a table? (SP-03)
7. Was the change validated on one period or the smoke fixture before a full run? (EP-04)
8. Do business rules have an independent check? (EP-05)
9. If an FR, an AC or the architecture changed: are the review entry, PRD version, Plan and gate tests updated together? (EP-07)
10. Is any real data or derived real value about to be committed? (must be no)
