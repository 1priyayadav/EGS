# Data Model & Lineage

The core philosophy of the Breathe ESG data model is **immutable raw ingestion** and **trackable normalization**. 

We explicitly do NOT overwrite raw data, nor do we perform destructive edits on carbon records. Every analyst correction or new batch upload creates a traceable lineage event.

## Core Models

### 1. Ingestion Layer
*   **DataSource:** Defines the origin system (e.g., SAP, Utility Portal, Concur).
*   **SourceFieldMapping:** Configurable rules mapping chaotic source fields (e.g., `WERKS`, `Plant`, `Facility`) to canonical internal fields (`plant_code`). This allows dynamic onboarding of new CSV formats without code changes.
*   **IngestionBatch:** A single upload event (file or webhook payload) to group records.
*   **RawIngestionRecord:** The immutable source of truth. Stores the exact JSON/CSV row as `raw_payload`. Includes a cryptographic `record_hash` to natively prevent duplicates.

### 2. Normalization & Review Layer
*   **EmissionRecord:** The canonical unit of work for an analyst.
    *   **3-Way Payload Lineage:** 
        *   Linked `raw_record` (immutable)
        *   `auto_normalized_payload` (machine-inferred)
        *   `analyst_corrected_payload` (human-corrected, null if untouched)
    *   **Versioning:** Uses `superseded_by` and `is_active_version` so that when corrected invoices are uploaded, the old record is soft-deleted and explicitly linked to the new one, rather than mutated.
*   **UnitConversionRule:** Database-driven lookup for mapping `kWh`, `liters`, etc., to standard carbon calculation units, flagging non-standard conversions as assumptions.
*   **ReviewEvent:** Complete audit history. Captures `CREATED`, `AUTO_NORMALIZED`, `FLAGGED`, `EDITED`, `APPROVED`, `REJECTED`, and `SUPERSEDED` actions with the user responsible.

## The Analyst Workflow
When an analyst edits a flagged record (e.g., fixing an impossible airport pair):
1. The machine-inferred `auto_normalized_payload` remains intact.
2. The `analyst_corrected_payload` is saved with their manual override.
3. A `ReviewEvent` is generated with a mandatory `correction_reason`.
4. The record returns to `PENDING` until it is explicitly signed off (`APPROVED`), at which point `is_locked` is set to True.
