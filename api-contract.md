# ASPARe Dashboard — API / Data Contract

**Purpose:** Defines the new, additive, read-only data structures and aggregator helper methods needed to render the redesigned dashboard UI.  
**Constraint:** Do NOT modify existing backend logic in `src/aspare/reporting/*.py`. Add new methods to `ReportingAggregator` (or a new dashboard-only reader module) that consume the existing `DashboardSnapshot` + inventory.  
**Consumer:** Streamlit dashboard (`dashboard/app.py`).  
**Format:** Additive only — existing `FindingRow`, `ActivityRow`, `DashboardSnapshot` fields remain unchanged.

---

## 1. New data structures (dashboard-only)

### 1.1 SeverityDistribution
```python
@dataclass
class SeverityDistribution:
    critical: int
    high: int
    medium: int
    low: int
    total: int
```
Used by: severity distribution bar chart.

### 1.2 DataClassBreakdown
```python
@dataclass
class DataClassBucket:
    data_class: str
    bucket_count: int
    protected_count: int      # buckets where all critical controls pass
    exposed_count: int        # bucket_count - protected_count
    hue_hex: str              # DESIGN.md data-class color token
    impact_statement: str     # human-readable impact (see §3)

@dataclass
class DataClassBreakdown:
    classes: list[DataClassBucket]
    total_buckets: int
    total_sensitive_buckets: int
    total_protected_sensitive: int
```
Used by: data-class breakdown chart + human impact cards.

### 1.3 RemediationOutcome
```python
@dataclass
class RemediationOutcome:
    successful: int
    failed: int
    total: int
    success_rate_pct: float   # 0..100, rounded to whole number
```
Used by: remediation success-rate chart + metric.

### 1.4 PipelineStage
```python
@dataclass
class PipelineStage:
    key: str                  # "detect" | "classify" | "remediate" | "verify" | "audit"
    label: str                # "Detect" / "Classify" / ...
    description: str
    status: str               # "pending" | "active" | "complete"
    order: int                # 1..5
```
Used by: pipeline flow section.

### 1.5 HumanImpactSummary
```python
@dataclass
class HumanImpactSummary:
    protected_classes: list[DataClassBucket]   # sensitive classes with count > 0, ordered
    one_line_narrative: str                    # e.g. "Protecting student records and patient health data across 12 buckets."
```
Used by: human impact section + hero narrative strip.

---

## 2. New aggregator methods (additive)

All methods are read-only and accept data already in memory (`DashboardSnapshot`, inventory list, session state).

### 2.1 `severity_distribution(snapshot) -> SeverityDistribution`
Counts findings by `row.severity`. Falls back to zeros for missing severities.

### 2.2 `remediation_outcome(snapshot) -> RemediationOutcome`
- `successful` = `snapshot.successful_remediations`
- `failed` = `snapshot.failed_remediations`
- `total` = successful + failed
- `success_rate_pct` = round(successful / total * 100) if total > 0 else 0

### 2.3 `data_class_breakdown(inventory, snapshot) -> DataClassBreakdown`
- Group inventory buckets by `tags.DataClass`.
- `bucket_count` = number of buckets with that class.
- `protected_count` = buckets with no CRITICAL/HIGH findings in `snapshot.findings` for that resource.
- `exposed_count` = bucket_count - protected_count.
- `hue_hex` and `impact_statement` from the static map (§3 below).
- Sort: sensitive classes first (FERPA, PHI, FINANCIAL, PII, SECRETS), then others alphabetically; within, descending bucket_count.
- Filter: include only classes with `bucket_count > 0`.

### 2.4 `human_impact_summary(breakdown) -> HumanImpactSummary`
- `protected_classes` = classes from breakdown where data class is in the sensitive set {FERPA, PHI, FINANCIAL, PII, SECRETS} and bucket_count > 0, capped at 5.
- `one_line_narrative` = composed string listing top 1–2 classes and total protected buckets.

### 2.5 `pipeline_state(session_step, has_records) -> list[PipelineStage]`
Maps `st.session_state.step` + audit-record presence to stage statuses (see specs/dashboard.md §7.4 table).

### 2.6 `data_class_for_resource(resource, inventory) -> str | None`
Looks up a bucket's `tags.DataClass` by resource name. Used to tag estate-table rows and issue-group headers.

---

## 3. Static human-impact map (dashboard config, no backend change)

A dashboard-only dict keyed by DataClass. Do not store in backend config files; keep in `dashboard/` or a new `dashboard/config/` module.

| DataClass | hue_hex | impact_statement | sensitive |
|-----------|---------|------------------|-----------|
| FERPA | `#60a5fa` | "Protecting student transcripts, enrollment, and financial-aid records." | yes |
| PHI | `#fb7185` | "Protecting patient clinic visits and consent records." | yes |
| FINANCIAL | `#f59e0b` | "Protecting payroll and tax batch records." | yes |
| PII | `#a78bfa` | "Protecting student IDs, HR, and housing records." | yes |
| SECRETS | `#c084fc` | "Protecting infrastructure credentials and deployment artifacts." | yes |
| AUDIT | `#94a3b8` | "Protecting CloudTrail and security audit trails." | no |
| BACKUP | `#2dd4bf` | "Protecting database snapshots and home-directory backups." | no |
| LEGAL | `#6366f1` | "Protecting legal holds and e-discovery material." | no |
| SENSITIVE | `#fb923c` | "Protecting quarantined and classified findings." | no |
| INTERNAL | `#22d3ee` | "Protecting internal analytics and CI artifacts." | no |
| PUBLIC | `#4ade80` | "Protecting public-facing marketing and media assets." | no |

---

## 4. Existing structures reused (no change)

| Structure | Fields used by dashboard |
|-----------|--------------------------|
| `DashboardSnapshot` | `resources_scanned`, `total_findings`, `critical_findings`, `high_findings`, `medium_findings`, `successful_remediations`, `failed_remediations`, `findings`, `activity` |
| `FindingRow` | `resource`, `rule`, `severity`, `status`, `remediation`, `verification`, `before_state`, `after_state`, `detected_at` |
| `ActivityRow` | `resource`, `issue`, `action`, `result`, `verified`, `timestamp`, `message`, `before_state`, `after_state` |
| Inventory bucket | `name`, `tags.DataClass`, `tags.Purpose`, `tags.Environment` |

---

## 5. Streamlit-side data contract (what the dashboard receives)

| UI section | Data needed | Method |
|------------|-------------|--------|
| Metrics | buckets count, total/critical/high findings, verified/failed | `snapshot` fields + `remediation_outcome` |
| Hero narrative strip | one-line impact sentence | `human_impact_summary` |
| Severity chart | severity counts | `severity_distribution` |
| Remediation chart | verified/failed/rate | `remediation_outcome` |
| Data-class chart | class → bucket count + hue | `data_class_breakdown` |
| Human impact cards | class → count + impact statement + hue | `data_class_breakdown` + `human_impact_summary` |
| Estate table | per-bucket data class + findings counts | `data_class_for_resource` + `snapshot.findings` |
| Pipeline flow | stage labels + statuses | `pipeline_state` |
| Remedy log | activity rows + result chips | `snapshot.activity` |

---

## 6. Version & change policy

- Version: `1.0.0`
- Additive only: existing fields/methods never removed or renamed.
- New aggregator methods return plain dataclasses (JSON-serializable via `dataclasses.asdict`) so the Streamlit layer can cache with `st.cache_data` if desired.
- If the backend aggregator is later refactored, these dashboard helpers should be re-pointed at the new source without changing field names.
