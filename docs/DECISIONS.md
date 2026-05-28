# Architectural Decisions

## 1. PostgreSQL Migration (Replacing SQLite)
Decided to migrate from SQLite to PostgreSQL to natively support JSONB indexing and concurrent audit logging, explicitly rejecting SQLite to ensure enterprise credibility. SQLite lacks true robust JSON indexing and struggles with concurrent write-heavy ingestion streams.

## 2. Dynamic Mappings vs Hardcoding
Decided to implement `SourceFieldMapping` rather than hardcoding column names in code. Real enterprise data from SAP or regional utilities comes with multilingual or inconsistent headers. This model allows ops teams to configure mappings in the database per-tenant.

## 3. Explicit Versioning over Mutation
Decided to implement a superseding record strategy for duplicate/revised batches rather than mutating approved records, protecting the audit trail. If a utility bill is re-uploaded with a correction, we insert the new record and update `is_active_version=False` on the old one, pointing `superseded_by` to the new ID.

## 4. Scope Categorization & Source Subsets
Decided to strictly limit the boundaries of the prototype to very specific subsets of each source:
*   **SAP (ERP):** We handle ONLY stationary fuel consumption (mapped strictly to Scope 1). We explicitly ignored purchased goods/services, capital goods, and logistics, which usually represent 80% of SAP data but are too complex for a 4-day ingestion pipeline.
*   **Utility Portals:** We handle ONLY electricity consumption (mapped strictly to Scope 2). We explicitly ignored natural gas, water, and waste, which use entirely different units (CCF, Gallons) and require vastly different anomaly detection thresholds.
*   **Corporate Travel:** We handle ONLY commercial flights (mapped strictly to Scope 3 - Category 6). We explicitly ignored hotel stays, rental cars, and rail travel, which require different APIs and calculation methodologies.

## 5. Explicit 3-Way Payload Lineage
Decided to separate `raw_payload`, `auto_normalized_payload`, and `analyst_corrected_payload`. If an auditor asks "Why is this number X?", we can prove exactly what the client uploaded, what our code assumed, and what the analyst manually overwrote.

---

## 6. What I would ask the Product Manager (PM)

If I had access to the PM before building this, I would raise the following critical product ambiguities:

1.  **Multi-Leg Flight Interpolation:** *"For travel data, when we receive an origin and destination airport code, should the system attempt to infer layovers based on standard flight routes, or do we strictly calculate the great-circle distance between the provided bookends? The latter under-reports Scope 3 emissions significantly."*
2.  **Materiality Thresholds for Anomalies:** *"Right now, any missing meter ID or unknown plant code throws a hard flag requiring human review. For enterprise clients uploading 50,000 rows, this could overwhelm analysts. Should we implement a materiality threshold (e.g., auto-approve anomalies if the estimated carbon impact is < 0.1% of the total batch)?"*
3.  **Superseding vs Delta Overwrites:** *"When a client re-uploads an SAP export, they usually just upload a longer date range that overlaps with the old one. Do you want the ingestion pipeline to supersede at the batch level (retracting the entire previous upload), or supersede at the individual row level based on a unique composite key (like Date + Plant Code + Material)?"*
