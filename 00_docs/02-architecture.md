# Architecture

This document describes the end-to-end architecture for the Fabric IQ demo
for Betrimex (Cocoxim), illustrating the OneLake medallion pattern feeding
into a certified semantic ontology and exposed via a bilingual Fabric Data
Agent.

Overview
 - Ingest raw collection and plant data into OneLake (Bronze).
 - Cleanse, normalize, and validate in Silver layers.
 - Curate business-ready tables and metrics in Gold (medallion → semantic).
 - Publish a certified semantic model (ontology) for BI and the Data Agent.
 - Expose natural-language access through the Fabric Data Agent (VN / EN).

Medallion Layers (OneLake)
- Bronze (raw): store original CSVs, sensor dumps, and collection logs partitioned by `ingest_date`.
	- Preserve source fidelity; minimal transformations.
- Silver (cleansed): apply schema normalization, type checks, unit conversions (e.g., Brix measurement normalization), and basic QA rules.
	- Implement data quality checks and lineage.
- Gold (curated / business): aggregated facts and dimensional models (e.g., `dim_farmer`, `dim_lot`, `fact_processing_run`).
	- Compute KPIs such as actual_yield, rejection_rate, and average_brix.

Semantic Model / Ontology
- Map curated gold tables to semantic entities using Fabric semantic model conventions.
	- Define certified business terms (e.g., `Brix`, `Lot`, `Grade`) with descriptions and data types.
- Expose measures and hierarchies for analytics (e.g., plant → line → production_run).
- Apply Row-Level Security (RLS) policies where needed (farmers, cooperatives, plant-level access).

Fabric Data Agent
- Connects to the published semantic model and OneLake-backed tables.
- Accepts VN/EN natural-language queries and translates intent into semantic queries.
- Uses prompt engineering and the repository's `04_data_agents/` artifacts (prompts, RLS rules) for behavior.
- Returns answers with table-level provenance and links to dashboards or notebook queries.

Notebooks & Orchestration
- Notebooks under `02_notebooks/` demonstrate ingest (`01_bronze_ingest.ipynb`), cleanse (`02_silver_cleanse.ipynb`), and curation (`03_silver_curate.ipynb`).
- Orchestration can be scheduled via Fabric job pipelines or external orchestrators to keep medallion layers fresh.

Security, Governance & Ops
- Use OneLake access controls and Fabric governance to manage dataset publishing and certified models.
- Track lineage from Bronze → Gold and expose quality metrics for monitoring.
- Define operational runbooks for data freshness, drift detection, and retraining of any ML models.

Pilot & Scaling Considerations
- Start with a 3-month pilot ingesting synthetic data, verify KPIs and agent accuracy, then connect live collection points.
- Scale considerations: partitioning strategy, vacuum/compaction cadence, and semantic model versioning.

References & Next Steps
- Validate semantic terms in `03_semantic-model/` and agent prompts in `04_data_agents/`.
- Run the notebooks in `02_notebooks/` to populate sample tables and verify the pipeline.

