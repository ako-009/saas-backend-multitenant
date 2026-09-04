# 🏢 Scalable Multi-Tenant B2B SaaS Backend

![Python](https://img.shields.io/badge/Python-3.11-blue?style=flat-square&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green?style=flat-square&logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?style=flat-square&logo=postgresql)
![Redis](https://img.shields.io/badge/Redis-7.2-red?style=flat-square&logo=redis)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?style=flat-square&logo=docker)
![AWS](https://img.shields.io/badge/AWS-S3-orange?style=flat-square&logo=amazonaws)

> A production-ready multi-tenant SaaS backend with schema-level PostgreSQL isolation, role-based access control, and AWS S3 document management — built for B2B enterprise scale.

---

## 📌 Problem Statement

B2B SaaS platforms (Freshdesk, Zoho, Notion for Teams) must serve multiple organizations on shared infrastructure while guaranteeing:
- **Complete data isolation** — one tenant must never see another's data
- **Granular access control** — admin, manager and user roles per tenant
- **Secure file storage** — per-tenant document isolation in cloud storage
- **Performance at scale** — fast responses under high multi-tenant load

This backend solves all four using PostgreSQL schema-based isolation, JWT-RBAC, AWS S3 with pre-signed URLs and Redis caching.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Applications                      │
│              (Web App / Mobile App / API Clients)           │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTPS
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Gateway                           │
│           Tenant Resolution + JWT Validation                │
└──────┬────────────────┬───────────────────┬─────────────────┘
       │                │                   │
       ▼                ▼                   ▼
┌──────────┐    ┌──────────────┐    ┌──────────────┐
│   Auth   │    │    Tenant    │    │   Document   │
│ Service  │    │   Service    │    │   Service    │
│  (JWT)   │    │  (RBAC)      │    │  (AWS S3)    │
└──────────┘    └──────┬───────┘    └──────┬───────┘
                       │                   │
                       ▼                   ▼
              ┌──────────────┐    ┌──────────────┐
              │  PostgreSQL  │    │    AWS S3    │
              │Schema-per-   │    │  Pre-signed  │
              │  Tenant      │    │    URLs      │
              └──────┬───────┘    └──────────────┘
                     │
                     ▼
              ┌──────────────┐
              │    Redis     │
              │  Cache-aside │
              └──────────────┘
```

---

## ✨ Key Features

| Feature | Implementation | Benefit |
|---|---|---|
| Tenant Isolation | PostgreSQL schema-per-tenant | Zero cross-tenant data leakage |
| Role-Based Access | JWT + RBAC middleware | Admin/Manager/User permission tiers |
| File Storage | AWS S3 + pre-signed URLs | Secure per-tenant document management |
| Performance | Redis cache-aside pattern | 97% API latency reduction |
| Onboarding | Automated schema provisioning | New tenant live in < 2 seconds |
| Scalability | Stateless API + Docker | Horizontal scaling ready |

---

## 🔐 Multi-Tenancy Model

This system uses **Schema-Based Isolation** — the most secure multi-tenancy pattern:

```
PostgreSQL Instance
├── public schema          (shared: tenant registry)
├── tenant_acme_corp       (Acme Corp's isolated data)
├── tenant_techco          (TechCo's isolated data)
└── tenant_startup         (Startup's isolated data)
```

**Why schema-based over row-level isolation?**
- No risk of missing `WHERE tenant_id =` in queries
- PostgreSQL `search_path` enforces automatic isolation at DB level
- Cross-tenant access is structurally impossible
- Independent schema per tenant — clean separation

**Schema Provisioning Flow:**
```
POST /tenants/register
    → validate + generate slug
    → INSERT into public.tenants
    → CREATE SCHEMA tenant_{slug}
    → CREATE TABLE users, documents, settings
    → COMMIT (atomic transaction)
    → Done in ~127ms
```

---

## 🔑 JWT Token Structure

Every request carries tenant context and role inside the JWT — no extra DB lookup needed:

```json
{
  "sub": "139ab52d-44aa-4ff8-a443-892dfcba23a0",
  "tenant_id": "acme_corp",
  "role": "admin",
  "exp": 1788463702,
  "iat": 1788461902
}
```

---

## 🛡️ RBAC Permission Matrix

| Permission | Admin | Manager | User |
|---|---|---|---|
| users:list | ✅ | ✅ | ❌ |
| users:invite | ✅ | ❌ | ❌ |
| users:delete | ✅ | ❌ | ❌ |
| users:update_role | ✅ | ❌ | ❌ |
| documents:upload | ✅ | ✅ | ❌ |
| documents:delete | ✅ | ❌ | ❌ |
| documents:list | ✅ | ✅ | ✅ |
| settings:read | ✅ | ✅ | ❌ |
| settings:update | ✅ | ❌ | ❌ |
| profile:read | ✅ | ✅ | ✅ |

---

## ☁️ AWS S3 Pre-signed URL Flow

```
1. Client → POST /documents/upload-url
2. API    → generates pre-signed S3 URL (15 min expiry)
3. Client → uploads directly to S3 (API server never touches file)
4. Client → POST /documents/confirm (save metadata to DB)

S3 Key Structure: {tenant_slug}/{user_id}/{uuid}/{filename}
Example: acme_corp/139ab52d.../a1b2c3.../report.pdf
```

API server never handles file bytes → zero file handling load.

---

## ⚡ Redis Caching Strategy

Cache-aside pattern with tenant-namespaced keys:

```
Key format: tenant:{tenant_id}:{resource}
Example:    tenant:acme_corp:users

Flow:
1. Check Redis → HIT → return in ~7ms
2. MISS → query PostgreSQL → store in Redis (TTL: 60s) → return
3. On any write → invalidate cache key immediately
```

---

## 📁 Project Structure

```
saas-backend-multitenant/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── auth.py            # Login, register
│   │   │   ├── tenants.py         # Tenant registration
│   │   │   ├── users.py           # User management
│   │   │   └── documents.py       # S3 document management
│   │   └── middleware/
│   │       └── rbac.py            # JWT decode + permission enforcement
│   ├── core/
│   │   ├── config.py              # Environment settings
│   │   ├── security.py            # JWT + bcrypt
│   │   └── database.py            # Dynamic schema switching
│   ├── models/
│   │   ├── tenant.py              # Tenant model (public schema)
│   │   ├── user.py                # User model (tenant schema)
│   │   └── document.py            # Document metadata model
│   ├── services/
│   │   ├── tenant_service.py      # Schema provisioning
│   │   ├── auth_service.py        # Authentication logic
│   │   ├── user_service.py        # User operations + cache
│   │   ├── document_service.py    # S3 pre-signed URL generation
│   │   └── cache_service.py       # Redis cache-aside
│   ├── storage/
│   │   └── s3_client.py           # boto3 S3 client
│   └── main.py
├── tests/
│   └── load/
│       └── locustfile.py          # Locust load test
├── benchmark.py                   # Redis latency benchmark
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 📊 Actual Benchmark Results

**Redis Cache Benchmark**
```
Request  1 (cache MISS): 275ms  ← PostgreSQL query
Request  2 (cache HIT):   10ms  ← Redis
Request  3+:               7ms  ← Redis

Latency reduction: 97% (CV target was 60%)
```

**Locust Load Test (50 concurrent users, 30 seconds)**
```
GET /users/      → 334 requests | 10ms median | 0 failures
GET /users/me    → 264 requests | 11ms median | 0 failures
GET /documents/  → 143 requests | 11ms median | 0 failures
Total            → 892 requests | 0 failures  | 30 req/s
```

**Tenant Schema Provisioning**
```
POST /tenants/register → schema provisioned in ~127ms
Tables created: users, documents, settings
Target was < 2000ms — achieved in 127ms
```

---

## 🔌 API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/tenants/register` | Public | Register tenant + provision schema |
| GET | `/tenants/{id}` | Admin | Get tenant details |
| POST | `/auth/register/{slug}` | Public | Register user for tenant |
| POST | `/auth/login/{slug}` | Public | Login → JWT token |
| GET | `/users/` | Admin/Manager | List tenant users |
| POST | `/users/invite` | Admin | Invite new user |
| PUT | `/users/{id}/role` | Admin | Update user role |
| DELETE | `/users/{id}` | Admin | Deactivate user |
| GET | `/users/me` | All | Own profile |
| POST | `/documents/upload-url` | Admin/Manager | Get S3 pre-signed URL |
| POST | `/documents/confirm` | Admin/Manager | Save document metadata |
| GET | `/documents/` | All | List tenant documents |
| DELETE | `/documents/{id}` | Admin | Delete document |

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/ako-009/saas-backend-multitenant.git
cd saas-backend-multitenant

# Environment
cp .env.example .env

# Start services (PostgreSQL + Redis + MinIO)
docker compose up postgres redis minio -d

# Install dependencies
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Run
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` for Swagger UI.

---

## 🎯 Design Decisions

**Schema-per-tenant vs Row-level security**
Schema isolation was chosen because cross-tenant access is structurally impossible — the database itself enforces it. Row-level security relies on every query having the correct WHERE clause, which is a single developer mistake away from a data breach.

**Pre-signed URLs for S3**
Clients upload directly to S3 using time-limited pre-signed URLs. The API server never handles file bytes — eliminating file handling load, memory pressure, and bandwidth costs entirely.

**Redis cache-aside**
Cache keys are namespaced by tenant_id (`tenant:acme_corp:users`) — mirroring database schema isolation at the cache layer. TTL of 60 seconds with explicit invalidation on writes ensures consistency.

**JWT with embedded tenant context**
Embedding `tenant_id` and `role` in the JWT payload means every request is self-contained. Middleware resolves both tenant context and RBAC permissions with a single token decode — no extra DB round trip.

---

## 🎓 Interview Q&A

**Q: What is multi-tenancy? What are the three models?**
Shared tables with tenant_id column (row-level), separate schema per tenant (schema-level), or separate database per tenant. Schema-per-tenant balances isolation and operational simplicity.

**Q: Why schema-per-tenant over row-level isolation?**
A missing WHERE clause in row-level isolation leaks all tenant data. Schema isolation makes that structurally impossible — wrong schema means no data, not wrong data.

**Q: How does your RBAC system work?**
JWT contains the user's role. `require_permission("users:invite")` is a FastAPI dependency factory that checks the permission matrix. No DB lookup — the token carries everything needed.

**Q: What is a pre-signed URL?**
A time-limited S3 URL cryptographically signed with AWS credentials. Anyone with the URL can upload exactly one file to exactly one location for exactly 15 minutes. After expiry, the URL is useless.

**Q: What did you cache in Redis?**
User lists — read-heavy, change rarely. Keys namespaced by tenant (`tenant:acme_corp:users`). TTL 60 seconds with explicit invalidation on any write operation.

**Q: What happens if schema provisioning fails midway?**
Everything runs in a single atomic transaction. If CREATE TABLE documents fails after CREATE TABLE users succeeded, the entire transaction rolls back — no partially provisioned tenants.

**Q: How would you scale this to 10,000 tenants?**
Connection pooling with PgBouncer, read replicas for each tenant group, Redis Cluster for cache, S3 lifecycle policies for document archival, and horizontal API scaling behind a load balancer.

---

## 🛠️ Tech Stack

| Component | Technology | Version |
|---|---|---|
| Framework | FastAPI | 0.110.0 |
| Database | PostgreSQL | 15 |
| Cache | Redis | 7.2 |
| Storage | AWS S3 / MinIO | - |
| Auth | JWT + bcrypt | - |
| ORM | SQLAlchemy (async) | 2.0.29 |
| Load Testing | Locust | 2.24.0 |
| Container | Docker Compose | - |

---

## 👤 Author

**Abhishek Kumar Ojha**
B.S.-M.S. (5YR) Chemistry | IIT Kharagpur | 22CY23003

[![GitHub](https://img.shields.io/badge/GitHub-ako--009-black?style=flat-square&logo=github)](https://github.com/ako-009)

