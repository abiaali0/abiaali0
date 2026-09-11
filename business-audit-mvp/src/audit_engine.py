from __future__ import annotations

import ipaddress
import socket
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = "AuditLead/1.0 (+website-audit; respectful-lightweight-checks)"
DEFAULT_TIMEOUT = 10


class AuditError(ValueError):
    """Raised when a target cannot be audited safely or successfully."""


@dataclass
class Check:
    key: str
    label: str
    status: str  # pass | warn | fail
    detail: str
    weight: int

    @property
    def points(self) -> float:
        multiplier = {"pass": 1.0, "warn": 0.5, "fail": 0.0}[self.status]
        return self.weight * multiplier


def normalize_url(raw_url: str) -> str:
    value = (raw_url or "").strip()
    if not value:
        raise AuditError("A URL is required.")
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise AuditError("Only public http/https URLs are supported.")
    return value


def _assert_public_host(url: str) -> None:
    host = urlparse(url).hostname
    if not host:
        raise AuditError("URL has no hostname.")
    try:
        addresses = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise AuditError(f"Could not resolve hostname: {host}") from exc

    for entry in addresses:
        address = entry[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            continue
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            raise AuditError("Private or non-public network targets are not allowed.")


def _request(session: requests.Session, url: str, timeout: int) -> requests.Response:
    response = session.get(url, timeout=timeout, allow_redirects=True)
    _assert_public_host(response.url)
    return response


def _status(value: bool, warn: bool = False) -> str:
    if value:
        return "pass"
    return "warn" if warn else "fail"


def _check(key: str, label: str, status: str, detail: str, weight: int) -> Check:
    return Check(key=key, label=label, status=status, detail=detail, weight=weight)


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _package(score: int) -> dict[str, Any]:
    if score < 50:
        return {
            "name": "Full Digital Upgrade",
            "price": "Starting at $900",
            "reason": "The site has multiple high-impact areas that may benefit from a broader rebuild or technical upgrade.",
        }
    if score < 75:
        return {
            "name": "Complete Digital Refresh",
            "price": "$600 one time",
            "reason": "There are several meaningful improvements that fit a focused refresh project.",
        }
    return {
        "name": "Digital Cleanup",
        "price": "$350 one time",
        "reason": "The fundamentals are fairly strong, so a smaller cleanup/optimization project may be enough.",
    }


def _recommendations(checks: list[Check], broken_links: list[str]) -> list[str]:
    mapping = {
        "https": "Use HTTPS everywhere and redirect HTTP traffic to the secure version.",
        "status": "Fix server or routing errors so the main page returns a successful response.",
        "speed": "Reduce response time with caching, optimized assets, and lighter page dependencies.",
        "title": "Write a clear, unique page title around 30–60 characters.",
        "meta": "Add a compelling meta description around 120–160 characters.",
        "h1": "Use one clear H1 that describes the page's primary topic or service.",
        "viewport": "Add a responsive viewport meta tag for better mobile rendering.",
        "canonical": "Add a canonical URL to reduce duplicate-content ambiguity.",
        "alts": "Add descriptive alt text to meaningful images.",
        "schema": "Add relevant structured data (for example LocalBusiness/Organization) where appropriate.",
        "robots": "Publish a valid robots.txt file and review crawl directives.",
        "sitemap": "Publish an XML sitemap and keep it current.",
        "contact": "Make phone/email/contact options easy to find on the page.",
        "cta": "Use a prominent call to action such as Book, Contact, Request a Quote, or Get Started.",
        "social": "Link the business's active social profiles from the website.",
    }
    items = [mapping[c.key] for c in checks if c.status != "pass" and c.key in mapping]
    if broken_links:
        items.append(f"Fix sampled internal links that returned errors ({min(len(broken_links), 5)} shown in the report).")
    return items[:8]


def audit_website(raw_url: str, timeout: int = DEFAULT_TIMEOUT, max_internal_links: int = 8) -> dict[str, Any]:
    url = normalize_url(raw_url)
    _assert_public_host(url)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    started = time.perf_counter()
    try:
        response = _request(session, url, timeout)
    except requests.RequestException as exc:
        raise AuditError(f"Could not load the website: {exc}") from exc
    elapsed = time.perf_counter() - started

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type.lower():
        raise AuditError("The target did not return an HTML page.")

    soup = BeautifulSoup(response.text, "html.parser")
    final_url = response.url
    parsed_final = urlparse(final_url)

    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    meta_tag = soup.find("meta", attrs={"name": lambda x: x and x.lower() == "description"})
    meta = (meta_tag.get("content") or "").strip() if meta_tag else ""
    h1s = soup.find_all("h1")
    viewport = soup.find("meta", attrs={"name": lambda x: x and x.lower() == "viewport"})
    canonical = soup.find("link", attrs={"rel": lambda x: x and "canonical" in [str(v).lower() for v in (x if isinstance(x, list) else [x])]})
    images = soup.find_all("img")
    meaningful_images = [img for img in images if not img.get("role") == "presentation"]
    with_alt = [img for img in meaningful_images if (img.get("alt") or "").strip()]
    alt_ratio = 1.0 if not meaningful_images else len(with_alt) / len(meaningful_images)
    schema = soup.find_all("script", attrs={"type": "application/ld+json"})

    page_text = soup.get_text(" ", strip=True).lower()
    hrefs = [a.get("href", "") for a in soup.find_all("a")]
    contact_signal = (
        any(href.startswith("mailto:") or href.startswith("tel:") for href in hrefs)
        or "contact" in page_text
    )
    cta_words = ("book", "contact", "get started", "request a quote", "schedule", "appointment", "call now")
    cta_signal = any(word in page_text for word in cta_words)
    social_hosts = ("instagram.com", "facebook.com", "linkedin.com", "tiktok.com", "youtube.com", "x.com", "twitter.com")
    social_signal = any(any(host in href.lower() for host in social_hosts) for href in hrefs)

    checks: list[Check] = []
    checks.append(_check("https", "HTTPS", "pass" if parsed_final.scheme == "https" else "fail", f"Final URL uses {parsed_final.scheme.upper()}.", 8))
    status_ok = 200 <= response.status_code < 400
    checks.append(_check("status", "Main page status", "pass" if status_ok else "fail", f"HTTP {response.status_code}.", 12))
    speed_status = "pass" if elapsed <= 1.5 else ("warn" if elapsed <= 3.0 else "fail")
    checks.append(_check("speed", "Server response time", speed_status, f"Initial HTML response took {elapsed:.2f}s from the audit runner.", 10))
    title_status = "pass" if 30 <= len(title) <= 60 else ("warn" if title else "fail")
    checks.append(_check("title", "Page title", title_status, f"{len(title)} characters" if title else "No title found.", 8))
    meta_status = "pass" if 120 <= len(meta) <= 160 else ("warn" if meta else "fail")
    checks.append(_check("meta", "Meta description", meta_status, f"{len(meta)} characters" if meta else "No meta description found.", 8))
    h1_status = "pass" if len(h1s) == 1 else ("warn" if len(h1s) > 1 else "fail")
    checks.append(_check("h1", "H1 structure", h1_status, f"Found {len(h1s)} H1 element(s).", 6))
    checks.append(_check("viewport", "Mobile viewport", "pass" if viewport else "fail", "Responsive viewport meta tag found." if viewport else "No viewport meta tag found.", 6))
    checks.append(_check("canonical", "Canonical URL", "pass" if canonical else "warn", "Canonical tag found." if canonical else "No canonical tag found.", 4))
    alt_status = "pass" if alt_ratio >= 0.9 else ("warn" if alt_ratio >= 0.6 else "fail")
    checks.append(_check("alts", "Image alt text", alt_status, f"{len(with_alt)}/{len(meaningful_images)} sampled page images have non-empty alt text.", 6))
    checks.append(_check("schema", "Structured data", "pass" if schema else "warn", f"Found {len(schema)} JSON-LD block(s)." if schema else "No JSON-LD structured data found.", 5))

    origin = f"{parsed_final.scheme}://{parsed_final.netloc}"
    robots_ok = False
    sitemap_ok = False
    try:
        robots = _request(session, urljoin(origin, "/robots.txt"), timeout)
        robots_ok = robots.status_code == 200 and bool(robots.text.strip())
    except (requests.RequestException, AuditError):
        pass
    try:
        sitemap = _request(session, urljoin(origin, "/sitemap.xml"), timeout)
        sitemap_ok = sitemap.status_code == 200 and bool(sitemap.text.strip())
    except (requests.RequestException, AuditError):
        pass

    checks.append(_check("robots", "robots.txt", "pass" if robots_ok else "warn", "robots.txt found." if robots_ok else "robots.txt was not detected.", 5))
    checks.append(_check("sitemap", "XML sitemap", "pass" if sitemap_ok else "warn", "sitemap.xml found." if sitemap_ok else "sitemap.xml was not detected at the standard path.", 5))
    checks.append(_check("contact", "Contact signals", "pass" if contact_signal else "warn", "Contact method/signals detected." if contact_signal else "No obvious contact signal detected on the page.", 6))
    checks.append(_check("cta", "Call to action", "pass" if cta_signal else "warn", "Common conversion CTA detected." if cta_signal else "No obvious booking/contact CTA detected.", 6))
    checks.append(_check("social", "Social profile links", "pass" if social_signal else "warn", "At least one major social profile link detected." if social_signal else "No major social profile links detected.", 5))

    internal_urls: list[str] = []
    for href in hrefs:
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(final_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme in {"http", "https"} and parsed.netloc == parsed_final.netloc:
            cleaned = absolute.split("#", 1)[0]
            if cleaned not in internal_urls:
                internal_urls.append(cleaned)
        if len(internal_urls) >= max_internal_links:
            break

    broken_links: list[str] = []
    for link in internal_urls:
        try:
            linked = _request(session, link, timeout)
            if linked.status_code >= 400:
                broken_links.append(f"{linked.status_code} — {link}")
        except (requests.RequestException, AuditError):
            broken_links.append(f"unreachable — {link}")

    total_weight = sum(c.weight for c in checks)
    score = round(sum(c.points for c in checks) / total_weight * 100) if total_weight else 0

    return {
        "requested_url": url,
        "final_url": final_url,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "score": score,
        "grade": _grade(score),
        "response_seconds": round(elapsed, 2),
        "checks": [asdict(c) | {"points": c.points} for c in checks],
        "sampled_internal_links": len(internal_urls),
        "broken_internal_links": broken_links[:5],
        "recommendations": _recommendations(checks, broken_links),
        "suggested_package": _package(score),
        "disclaimer": "Lightweight technical/marketing diagnostic only; not a guarantee of rankings, revenue, accessibility compliance, or security.",
    }
