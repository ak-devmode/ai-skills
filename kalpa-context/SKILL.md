---
name: kalpa-context
description: "Kalpa Inovasi Digital context — WellMed product tiers, architecture, integrations, and project structure. Use when working on any Kalpa/WellMed codebase."
allowed-tools:
  - Read
  - Glob
  - Grep
---

# Kalpa Context

WellMed: Indonesian clinic HIS with SATU SEHAT integration. <10 person startup, Alex is infra lead/co-founder.

## Product Tiers & Services
- **Lite** (7 services): Praktik Mandiri — EMR, Cashier, Reporting, Appointment, Backbone, SATU SEHAT, BPJS
- **Plus** (13 services): Klinik Pratama — adds Pharmacy, Lab, Radiology, Outpatient, ED/IGD, Cashier+
- **Enterprise** (18 services): Klinik Utama — adds LIS+, RIS+, MCU, Inpatient, Warehouse
- **HQ** (separate): Subscription, billing, user management for SaaS

## Differentiators
AI assistants (ICD-10, SOAP), simple UI, native SATU SEHAT integration with status tracking/visualization.

## Architecture
- **Edge**: Nuxt.js frontends (WellMed + HQ) → Nitro BFF (security, sessions, reverse proxy) → Go Gateway
- **Internal**: gRPC sync between services, RabbitMQ async for external integrations
- **Data**: Multi-tenant (per-tenant DB, per-service schema, tables clustered by year). Redis cache (pub/sub invalidation). Elasticsearch for reporting/search.
- **Patterns**: SAGA orchestration (not choreography), ULID for IDs, zap JSON logging

## External Integrations
- **Government**: SATU SEHAT (FHIR), P-Care/BPJS, Mobile JKN
- **3rd Party**: Jurnal, Talenta, Xendit, Xero, Zoho Desk, Kyoo

## Go Project Structure
```
/internal/domain/{module}/  → handler/ service/ repository/ DTO/
/pkg/                       → shared libs (cache, validation, saga, queue)
/proto/                     → gRPC definitions
```
Service layer (80% coverage) owns all business logic. Repository = SQL only, tested via integration.

## Current State
Refactoring Laravel/FrankenPHP → Go. Lite port ~1 month out. Active: SATU SEHAT MOH rejections, AWS infra (ALB, cross-account DNS, CloudConnexa VPN).

## Notes
Internal docs in Bahasa Indonesia. No HIPAA (Indonesia) but security/audit are corporate values.
