# Repository Context for GitHub Copilot

## Project
This repo contains a Microsoft Fabric demo for **Contoso Manufacturing Company**, a Vietnamese
coconut processor (Ben Tre province, brand: Comaco). The demo showcases:
- OneLake (unified storage, medallion architecture)
- Fabric Ontology / Semantic Model (certified business definitions)
- Fabric Data Agent (bilingual VN/EN natural-language Q&A)

## Domain Vocabulary
- Farmer: smallholder coconut grower in Mekong Delta provinces (Ben Tre,
  Tra Vinh, Tien Giang, Vinh Long)
- Lot: a batch of coconuts delivered by a farmer at a collection point
- Brix: sugar content of coconut water (key quality measure)
- Grade A/B/C: coconut quality classification
- Production Run: a batch processed on a specific plant line
- Yield %: actual_yield / expected_yield

## Conventions
- All Python uses PySpark for Fabric notebook compatibility
- Table naming: dim_<entity>, fact_<process>
- All dates in ISO 8601, all timestamps in UTC, currency in VND or USD
- Sample data is SYNTHETIC — no real farmer PII
- Vietnamese strings use diacritics (UTF-8)

## Code style
- Type hints on all Python functions
- Docstrings in English; user-facing strings may be bilingual
- Prefer Delta tables, partition by date where relevant

## What NOT to suggest
- Don't recommend installing new packages (Fabric notebooks have a fixed env)
- Don't fabricate Contoso Manufacturing Company internal data — use only the synthetic dataset


