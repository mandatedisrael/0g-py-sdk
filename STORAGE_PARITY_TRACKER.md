# 0G Storage TS Starter Kit Parity Tracker

This repo treats [`0gfoundation/0g-storage-ts-starter-kit`](https://github.com/0gfoundation/0g-storage-ts-starter-kit) as the upstream source for storage wrapper features that may need to land in the Python storage SDK.

The Python package is lower-level than the starter kit, so not every TypeScript-only wrapper is automatically a missing Python SDK feature. Use the generated report as a triage input, then decide whether each item should become a Python API, example, script, or intentional difference.

## Workflow

1. Run the checker against the latest upstream starter kit:

   ```bash
   python3 scripts/check_storage_parity.py --refresh
   ```

2. Review `reports/storage_parity_report.md` for:

   - the `Coding Agent Brief` section, which is the primary handoff for implementation agents
   - `missing_in_python` feature probes
   - TypeScript-only wrapper functions
   - name-only matches that need manual behavior review

3. Use broader package scope when reviewing CLI scripts and the browser UI:

   ```bash
   python3 scripts/check_storage_parity.py --refresh --scope package
   ```

4. Classify each meaningful upstream change:

   - `port`: Python should implement the feature or behavior.
   - `example`: Python should add a script or example, not a core API.
   - `covered`: Python already supports it under a different name or lower-level API.
   - `intentional-difference`: Python intentionally diverges.
   - `docs-only`: No SDK behavior to port.
   - `needs-research`: Source-level review is needed before deciding.

5. Add or update Python parity tests for any ported behavior.

## Last Checked Upstream

- Commit: `6a308551f4a4d2ccb57dea0ec1adee35c4cbbfe3`
- Package version: `2.0.0`
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
| open | Client-side encryption | Storage upload/download | needs-research | Report flags `aes256`, `ecies`, and `EncryptionHeader` as missing from Python evidence. |
| open | `peekHeader` | Storage download/header inspection | needs-research | Report flags upstream `peekHeader` as missing in Python. |
| open | `StorageMode` standard/turbo config | Network configuration | needs-research | Report found only partial Python evidence for mode selection. |

## Intentional Differences

| Upstream Area | Python Area | Reason | Review Date |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |

## Shipped Parity Work

| Date | Upstream Reference | Python Change | Tests |
| --- | --- | --- | --- |
| TBD | TBD | TBD | TBD |
