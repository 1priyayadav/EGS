# Tradeoffs & Simplifications

Because this is a prototype built within a 4-day constraint, several intentional tradeoffs were made to prioritize end-to-end workflow coherence over raw feature breadth.

## 1. Synchronous vs Async Processing
Prototype processes synchronously for simplicity, but the ingestion and normalization tables are architecturally separated to support a scalable processing pipeline via future async workers (like Celery/RQ) and background jobs. Real-world batches of 10,000+ rows would cause API timeouts if processed synchronously.

## 2. Edge Cases Ignored
We intentionally ignore highly complex partial replay scenarios (e.g. selectively overwriting arbitrary rows without full batch context) to avoid overengineering an event-sourced database.

## 3. Utility Tariff Structures
While we capture units and misaligned billing periods, we deliberately DO NOT model utility tariff structures (e.g., peak vs off-peak financial rates). While critical for spend analysis, they are irrelevant for physical carbon mass accounting.

## 4. Carbon Engine Omission
We normalize physical units (e.g., liters of fuel, kWh of electricity) and perform anomaly detection, but we explicitly do NOT attempt to calculate the final `kgCO2e`. Emulating a real carbon accounting engine with geography-specific emission factors (EPA, DEFRA) is outside the scope of the ingestion pipeline.
