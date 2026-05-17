# 0G Compute TS SDK Parity Tracker

This repo treats [`0gfoundation/0g-compute-ts-sdk`](https://github.com/0gfoundation/0g-compute-ts-sdk) as the upstream source of truth for the Python inference SDK.

## Workflow

1. Run the checker against the latest upstream TS SDK:

   ```bash
   python3 scripts/check_compute_parity.py --refresh
   ```

   Use the broader package scope when reviewing CLI/provider-controller/web UI parity:

   ```bash
   python3 scripts/check_compute_parity.py --refresh --scope package
   ```

2. Review `reports/compute_parity_report.md` for:

   - the `Coding Agent Brief` section, which is the primary handoff for implementation agents
   - `missing_in_python` feature probes
   - TypeScript-only classes, functions, and methods
   - name-only matches that need manual behavior review

3. For each meaningful upstream change, classify it:

   - `port`: Python should implement the feature or behavior.
   - `covered`: Python already supports it under a different name or shape.
   - `intentional-difference`: Python intentionally diverges.
   - `docs-only`: No SDK behavior to port.
   - `needs-research`: Source-level review is needed before deciding.

4. Add or update Python parity tests for any ported behavior.

## Last Checked Upstream

- Commit: `cee4e39e6b80ff31869b92bdad343fbc915493a3`
- Package version: `0.8.3`
- Date: `2026-05-17`
- Scope: `sdk`

## Last Reviewed Upstream

- Commit: `unreviewed`
- Package version: `unreviewed`
- Date: `unreviewed`
- Reviewer: `unreviewed`

## Open Parity Items

| Status | Upstream Area | Python Area | Decision | Notes |
| --- | --- | --- | --- | --- |
| open | TBD | TBD | needs-research | Run the parity checker and triage the generated report. |

## Intentional Differences

| Upstream Area | Python Area | Reason | Review Date |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

## Shipped Parity Work

| Date | Upstream Reference | Python Change | Tests |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |
