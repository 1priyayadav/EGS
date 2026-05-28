# Data Sources: Scope, Research, and Boundaries

This document details the research conducted on real-world ESG ingestion sources, justifies our prototype boundaries, explains our sample data construction, and outlines what would break in a real deployment.

---

## 1. SAP - Fuel and Procurement Data

### Format Researched & Chosen: Flat File (CSV via MB51 / SE16N)
*   **Research:** SAP data can be exported via IDocs (XML/flat file formats for B2B communication), BAPIs (callable remote functions), OData services (modern REST), or simple ALV grid exports (like MB51 for material documents or SE16N for raw tables). 
*   **Justification for Choice:** We explicitly chose the **ALV Grid CSV Export (MB51 - Material Document List)**. Why? Because most sustainability leads do not have direct API access to their company's SAP ERP. They usually ask the supply chain or facilities team for a report, and that team sends them an Excel/CSV dump of fuel materials consumed by plant. 
*   **What our Sample Data looks like:** It simulates a messy MB51 export. It contains German/inconsistent headers (`WERKS` for Plant, `MENGE` for Quantity, `MEINS` for Unit), negative quantities (indicating a goods issue reversal), and unknown plant codes.
*   **What would break in a real deployment:** 
    1.  *Character Encodings:* SAP exports are notoriously plagued by UTF-16LE or ANSI encodings depending on the user's GUI settings. A strict UTF-8 parser will fail.
    2.  *Number Formatting:* European SAP instances export `1.000,50` instead of `1000.50`. Our simple `float()` cast in `normalization.py` would crash.

---

## 2. Utility Data - Electricity

### Format Researched & Chosen: Portal CSV Export
*   **Research:** Facilities teams get electricity data via OCR/PDF scraping of physical bills, EDI 810 formats (automated billing), or CSV exports from utility portal dashboards (like PG&E or NextEra). 
*   **Justification for Choice:** We chose the **Utility Portal CSV Export**. OCR on PDFs is too brittle and requires specialized ML (like AWS Textract) which is outside the scope of a 4-day ingestion pipeline prototype. Portal CSVs represent a highly realistic, scalable "middle ground".
*   **What our Sample Data looks like:** It includes `meter_id`, `service_start_date`, `service_end_date`, `usage_kwh`, and `total_cost`. Crucially, the billing periods are 28, 31, or 33 days—rarely perfectly aligned to a calendar month.
*   **What would break in a real deployment:**
    1.  *Estimated vs Actual Reads:* Utilities often bill on estimated usage, then send a true-up bill 3 months later containing massive negative or positive adjustments. Our basic `superseded_by` logic handles full replacements, but struggles with multi-month retroactive true-ups.
    2.  *Rollover Meters:* If a physical meter is replaced mid-month, the portal often spits out two rows for the same period with different meter IDs, appearing as a duplication anomaly when it is actually additive.

---

## 3. Corporate Travel - Flights

### Format Researched & Chosen: JSON Webhook Payload (e.g., Navan / Concur API)
*   **Research:** Travel platforms like SAP Concur or Navan (formerly TripActions) provide robust REST APIs and webhook integrations for booked itineraries. They typically return JSON arrays containing passenger details, PNRs (Booking References), Origin/Destination IATA codes, and flight segment classes (Economy, Business).
*   **Justification for Choice:** We chose the **JSON API Webhook**. Unlike utilities, travel platforms are highly modernized. Sustainability platforms standardly ingest travel via automated API polling or webhook drops rather than manual file uploads.
*   **What our Sample Data looks like:** A JSON array containing `travel_type`, `origin_airport`, `destination_airport`, and `traveler_email`. It intentionally includes invalid/dummy airport codes (e.g., `XXX`) and missing emails to trigger our normalization heuristics.
*   **What would break in a real deployment:**
    1.  *Multi-Leg Flights:* A booking from SFO to LHR often contains a layover (SFO -> JFK -> LHR). Calculating great-circle distance on the aggregate PNR rather than the individual flight segments severely underestimates the actual flight distance (and thus emissions).
    2.  *Cancellations & Refunds:* Travel data is highly mutable. A webhook payload indicating a flight might be followed by a webhook 3 days later indicating a cancellation. Our prototype's idempotency logic (`record_hash`) would ingest both as additive emissions unless we explicitly modeled cancellation state reconciliation.
