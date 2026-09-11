# AuditLead — Automated Small-Business Website Audit Engine

AuditLead is a zero-API-cost website audit tool designed to turn public business websites into qualified service opportunities. It checks a site's technical and conversion basics, scores the site, creates a client-friendly HTML report, and recommends a service package.

## Why this can make money

The software itself does not magically produce income. It removes the repetitive part of selling digital services: reviewing websites one by one. Add businesses to a CSV, let the batch runner audit them, then use the reports as personalized proof of what you can fix.

Suggested starting offers (edit these to match the client and scope):

- **Digital Cleanup — $350 one time**: smaller website/Google/profile fixes and cleanup.
- **Complete Digital Refresh — $600 one time**: broader website, SEO, form, usability and digital-presence improvements.
- **Full Digital Upgrade — starting at $900**: substantial redesigns, new features, automations and larger technical work.

A future version can add a payment provider and paid self-service reports. The current MVP intentionally works without paid APIs or required cloud services.

## What it audits

- HTTPS and HTTP status
- page-load response time
- title and meta description
- H1 structure
- mobile viewport
- canonical tag
- image alt-text coverage
- structured data
- robots.txt
- sitemap.xml
- contact signals
- calls to action / booking signals
- social profile links
- a sample of internal links for broken-link signals

The engine produces a 0–100 score, a grade, prioritized recommendations, and an editable suggested package.

## Quick start

```bash
cd business-audit-mvp
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.app:app --reload
```

Open `http://127.0.0.1:8000` and enter a public website URL.

## Run a batch in the background

Copy the example prospect file:

```bash
cp data/prospects.example.csv data/prospects.csv
```

Edit `data/prospects.csv`:

```csv
business,url
Example Business,https://example.com
```

Then run:

```bash
python -m src.run_batch
```

Reports are written to `reports/` along with `results.csv` and `results.json`.

## GitHub Actions

The repository includes `.github/workflows/business-audit.yml`. Once this branch is merged into the default branch, the workflow can be started manually and also runs on a weekday schedule. It tests the project and generates audit artifacts from `business-audit-mvp/data/prospects.csv` when that file exists.

For privacy, prospect lists and generated reports are gitignored by default. Keep real prospect data out of a public repository.

## Branding reports

Optional environment variables:

```bash
AUDIT_BRAND_NAME="Your Business Name"
AUDIT_CONTACT_NAME="Your Name"
AUDIT_CONTACT_EMAIL="you@example.com"
AUDIT_CONTACT_PHONE=""
```

No secrets are required for the core audit engine.

## API

### `POST /api/audit`

```json
{
  "url": "https://example.com"
}
```

Returns the structured audit result as JSON.

### `GET /report?url=https://example.com`

Returns the client-friendly HTML report.

## Safety and limitations

- Only public `http`/`https` targets are allowed.
- Private, loopback, link-local and reserved IP ranges are blocked to reduce SSRF risk.
- The tool uses lightweight HTML/HTTP checks, not a full browser renderer.
- A score is a sales/diagnostic aid, not a guarantee of search ranking, revenue, accessibility compliance, or security.
- Respect website terms, robots directives, reasonable request rates, and applicable anti-spam/privacy laws when contacting businesses.

## Next revenue milestones

1. Run 20–50 audits on businesses you would realistically serve.
2. Prioritize low-scoring sites with clear, fixable issues.
3. Send a short personalized message offering the report and one specific fix.
4. Close one-time projects first.
5. Convert satisfied clients into monthly maintenance/automation retainers.
6. Later add payments + customer accounts for self-service paid audits.
