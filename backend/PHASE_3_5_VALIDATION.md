# Phase 3–5 backend validation marker

This file records the final integration-validation point for the Phase 3–5 backend after the tenant-bound session schema correction, the schema-version regression-test alignment to `CURRENT_SCHEMA_VERSION = 10`, and the correction that makes direct `init_db()` calls execute the Phase 4–5 schema initializer before readiness checks.

The associated `main` workflows are the authoritative post-merge validation for this state.
