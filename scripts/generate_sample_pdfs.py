"""
Generates a small, realistic placeholder PDF knowledge base for demoing the
ingestion + retrieval pipeline when the real corpus (shared via Google Drive
in the assessment brief) is not available in this environment.

Swap these out for the real documents by dropping PDFs into `sample_docs/`
(or any directory) and pointing the ingestion CLI at it -- see README.md.

Run: python3 scripts/generate_sample_pdfs.py
"""
import os

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_docs")
os.makedirs(OUT_DIR, exist_ok=True)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="H1", fontSize=18, leading=22, spaceAfter=14, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="H2", fontSize=13, leading=17, spaceBefore=12, spaceAfter=8, fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="Body", fontSize=10.5, leading=15, spaceAfter=8))


def build_pdf(filename, title, sections):
    path = os.path.join(OUT_DIR, filename)
    doc = SimpleDocTemplate(path, pagesize=LETTER,
                             topMargin=0.9 * inch, bottomMargin=0.9 * inch,
                             leftMargin=0.9 * inch, rightMargin=0.9 * inch)
    story = [Paragraph(title, styles["H1"]), Spacer(1, 6)]
    for heading, paragraphs in sections:
        story.append(Paragraph(heading, styles["H2"]))
        for p in paragraphs:
            if isinstance(p, list):  # table: list of rows
                t = Table(p, hAlign="LEFT")
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]))
                story.append(t)
                story.append(Spacer(1, 8))
            else:
                story.append(Paragraph(p, styles["Body"]))
    doc.build(story)
    print(f"wrote {path}")


# ---------------------------------------------------------------------------
# Doc 1: Cloud Architecture & Deployment Standards
# ---------------------------------------------------------------------------
build_pdf(
    "cloud_architecture_standards.pdf",
    "Cloud Architecture &amp; Deployment Standards",
    [
        ("1. Purpose and Scope", [
            "This document defines the mandatory architecture and deployment standards for all "
            "production services operated by the Platform Engineering organization. It applies to "
            "every service deployed to the shared Kubernetes clusters, regardless of the owning team.",
            "The standards cover service topology, deployment strategy, autoscaling policy, secrets "
            "management, and disaster recovery expectations. Teams that require an exception must file "
            "an architecture waiver with the Platform Review Board before launch.",
        ]),
        ("2. Service Topology", [
            "Services are organized into three tiers: edge (public-facing gateways and load balancers), "
            "application (stateless business-logic services), and data (databases, caches, and message "
            "queues). Application-tier services must be stateless and horizontally scalable; any local "
            "disk usage is treated as ephemeral and must not hold data required for correctness.",
            "Each service must expose a /healthz endpoint for liveness and a /readyz endpoint for "
            "readiness. Readiness checks must verify connectivity to all hard dependencies, including "
            "the primary database and any required message broker.",
        ]),
        ("3. Deployment Strategy", [
            "All production deployments use a rolling update strategy with a maximum surge of 25% and "
            "maximum unavailability of 0%. Canary releases are required for any service handling more "
            "than 1,000 requests per minute; canaries must run for at least 15 minutes and automatically "
            "roll back if the error rate exceeds 2% or p99 latency regresses by more than 30%.",
            "Rollbacks must be executable within 5 minutes via a single command or pipeline trigger. "
            "Blue/green deployments are permitted for services with strict zero-downtime requirements, "
            "such as the payments gateway.",
        ]),
        ("4. Autoscaling Policy", [
            "Horizontal Pod Autoscalers must be configured for every application-tier deployment, with "
            "a minimum of 3 replicas in production for high availability across zones. Scaling targets "
            "should be based on CPU utilization (70% target) and, where available, custom request-rate "
            "metrics.",
            [["Environment", "Min Replicas", "Max Replicas", "Target CPU"],
             ["dev", "1", "3", "80%"],
             ["staging", "2", "6", "75%"],
             ["production", "3", "50", "70%"]],
        ]),
        ("5. Secrets Management", [
            "Secrets must never be stored in source control, container images, or environment variable "
            "defaults checked into a repository. All secrets are provisioned via the central secrets "
            "manager and injected at runtime as mounted files or environment variables through the "
            "sidecar injector. Secrets are rotated automatically every 90 days for database credentials "
            "and every 30 days for API keys with external exposure.",
        ]),
        ("6. Disaster Recovery", [
            "Every stateful data store must have a documented Recovery Point Objective (RPO) and "
            "Recovery Time Objective (RTO). The default RPO is 15 minutes (via continuous WAL archiving "
            "for relational databases) and the default RTO is 60 minutes. Disaster recovery drills must "
            "be executed at least twice per year, with results logged in the DR runbook.",
        ]),
    ],
)

# ---------------------------------------------------------------------------
# Doc 2: Data Privacy and Security Policy
# ---------------------------------------------------------------------------
build_pdf(
    "data_privacy_security_policy.pdf",
    "Data Privacy &amp; Security Policy",
    [
        ("1. Overview", [
            "This policy establishes the baseline requirements for handling personal data, classifying "
            "information assets, and responding to security incidents. It applies to all employees, "
            "contractors, and systems that process customer or employee data.",
        ]),
        ("2. Data Classification", [
            "All data must be classified into one of four tiers: Public, Internal, Confidential, and "
            "Restricted. Restricted data includes government identifiers, financial account numbers, "
            "authentication credentials, and health information. Restricted data must be encrypted at "
            "rest using AES-256 and in transit using TLS 1.2 or higher, and access must be logged and "
            "reviewed quarterly.",
            [["Tier", "Examples", "Encryption at Rest", "Access Review"],
             ["Public", "Marketing pages", "Not required", "N/A"],
             ["Internal", "Internal wikis", "Recommended", "Annual"],
             ["Confidential", "Contracts, salaries", "Required", "Semi-annual"],
             ["Restricted", "SSNs, credentials, health data", "Required (AES-256)", "Quarterly"]],
        ]),
        ("3. Access Control", [
            "Access to Confidential and Restricted data follows the principle of least privilege and "
            "requires role-based access control (RBAC) with manager approval. Privileged access "
            "(administrator or database superuser roles) requires multi-factor authentication and "
            "expires automatically after 12 hours unless renewed through a break-glass procedure.",
        ]),
        ("4. Data Retention", [
            "Personal data collected for a specific purpose must not be retained longer than necessary "
            "to fulfill that purpose or to meet legal obligations. Standard retention for customer "
            "support transcripts is 24 months; billing records are retained for 7 years to satisfy "
            "financial audit requirements. Automated deletion jobs must run monthly and produce an "
            "auditable deletion report.",
        ]),
        ("5. Incident Response", [
            "Any suspected data breach must be reported to the Security team within 1 hour of "
            "discovery. The Security team classifies incidents by severity (SEV1-SEV4) and, for any "
            "incident involving Restricted data, notifies the Data Protection Officer within 24 hours. "
            "Regulatory notification timelines (e.g., 72 hours under GDPR) are tracked separately by "
            "the Legal team once an incident is confirmed to involve personal data of EU residents.",
        ]),
        ("6. Third-Party Vendors", [
            "Vendors that process Confidential or Restricted data on the company's behalf must sign a "
            "Data Processing Agreement and complete an annual security questionnaire. Vendor access to "
            "production systems must be time-boxed and reviewed by the vendor's sponsoring team before "
            "renewal.",
        ]),
    ],
)

# ---------------------------------------------------------------------------
# Doc 3: Product API Reference Guide (excerpt)
# ---------------------------------------------------------------------------
build_pdf(
    "product_api_reference_guide.pdf",
    "Product API Reference Guide (Excerpt)",
    [
        ("1. Authentication", [
            "All API requests must include an Authorization header with a bearer token obtained from "
            "the /oauth/token endpoint. Tokens are valid for 3600 seconds and must be refreshed using "
            "the associated refresh token before expiry. Requests without a valid token receive a 401 "
            "Unauthorized response with an error code of AUTH_TOKEN_MISSING or AUTH_TOKEN_EXPIRED.",
        ]),
        ("2. Rate Limiting", [
            "The API enforces a default rate limit of 600 requests per minute per API key, with burst "
            "capacity of 100 additional requests. Clients exceeding the limit receive a 429 Too Many "
            "Requests response and a Retry-After header indicating the number of seconds to wait. "
            "Enterprise plans may request a higher limit through the developer portal.",
            [["Plan", "Requests / min", "Burst", "Concurrent Connections"],
             ["Free", "60", "10", "5"],
             ["Pro", "600", "100", "50"],
             ["Enterprise", "6000", "1000", "500"]],
        ]),
        ("3. Pagination", [
            "List endpoints are paginated using cursor-based pagination. Responses include a next_cursor "
            "field; clients pass this value as the cursor query parameter to retrieve the next page. "
            "The default page size is 25 and the maximum is 200. Requesting a page size above the "
            "maximum returns a 400 Bad Request with error code INVALID_PAGE_SIZE.",
        ]),
        ("4. Error Handling", [
            "Errors are returned as JSON objects with the fields error_code, message, and request_id. "
            "Clients should log the request_id when contacting support. Retriable errors (429, 502, 503) "
            "should use exponential backoff starting at 500ms with a maximum of 5 retries.",
        ]),
        ("5. Webhooks", [
            "Webhook payloads are signed using HMAC-SHA256 with the shared webhook secret. Consumers "
            "must verify the X-Signature header before processing the payload and should respond with a "
            "2xx status within 10 seconds. Failed deliveries are retried with exponential backoff for up "
            "to 24 hours before being marked as permanently failed.",
        ]),
    ],
)

# ---------------------------------------------------------------------------
# Doc 4: Employee Handbook (excerpt) -- leave policy
# ---------------------------------------------------------------------------
build_pdf(
    "employee_handbook_leave_policy.pdf",
    "Employee Handbook: Leave &amp; Time-Off Policy (Excerpt)",
    [
        ("1. Paid Time Off (PTO)", [
            "Full-time employees accrue 1.75 days of PTO per month, for a total of 21 days per year. "
            "PTO accrual begins on the employee's start date and unused PTO may be carried over up to a "
            "maximum of 10 days into the following calendar year. Any balance beyond 10 days is forfeited "
            "unless local law requires otherwise.",
        ]),
        ("2. Sick Leave", [
            "Employees receive 10 days of paid sick leave per year, separate from PTO. Sick leave may be "
            "used for the employee's own illness or to care for an immediate family member. Absences "
            "longer than 3 consecutive days require a note from a healthcare provider.",
        ]),
        ("3. Parental Leave", [
            "Eligible employees receive 16 weeks of paid parental leave following the birth, adoption, "
            "or foster placement of a child. Leave must be taken within 12 months of the qualifying "
            "event and may be split into two blocks of at least 2 weeks each with manager approval.",
        ]),
        ("4. Bereavement Leave", [
            "Employees are entitled to 5 paid days of bereavement leave for the death of an immediate "
            "family member and 2 paid days for an extended family member. Additional unpaid leave may be "
            "requested through HR on a case-by-case basis.",
        ]),
        ("5. Requesting Time Off", [
            "All time-off requests must be submitted through the HR portal at least 2 weeks in advance "
            "for planned absences exceeding 3 days. Manager approval is required before the leave is "
            "confirmed; requests are auto-escalated to the department head if not actioned within 3 "
            "business days.",
        ]),
    ],
)

print("done")
