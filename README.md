## Business Case

Contoso Manufacturing Company (Comaco) needs a reliable, scalable data platform to improve
quality control, increase processing yield, and deliver timely insights
across its smallholder coconut supply chain in Ben Tre province.

This Fabric IQ demo shows a concrete implementation pattern using OneLake
medallion architecture, a certified semantic model, and a bilingual
Fabric Data Agent to enable operational decisioning and stakeholder
access to answers in Vietnamese and English.

Key problems addressed:
- Fragmented collection and inconsistent definitions (e.g., `Brix`, `Lot`).
- Manual QA decisions that increase rejections and waste.
- Slow time-to-insight for plant operations and farmer feedback.

Expected outcomes:
- Reduce quality rejections and product waste.
- Improve actual yield percentage and processing throughput.
- Shorten time-to-insight for QA and operations dashboards.

Success metrics (examples):
- Quality rejection rate (target: -10–30% vs baseline).
- Processing yield percentage (target: +2–8% vs baseline).
- Average time-to-insight for analytics (target: <24 hours).

Pilot plan: ingest synthetic/raw data into bronze, apply cleansing in silver,
publish a curated semantic model, and enable a bilingual data agent and
dashboards for a 3-month pilot. If successful, scale to production and
connect to live plant and collection-point data within 6–12 months.

Stakeholders: operations, quality assurance, supply chain, and farmer
cooperatives.

Next steps: run the notebooks under `02_notebooks/` to populate sample
tables, verify semantic model definitions, and iterate on agent prompts
in `04_data_agents/`.



