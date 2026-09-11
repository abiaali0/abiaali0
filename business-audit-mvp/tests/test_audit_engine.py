import pytest

from src.audit_engine import AuditError, _grade, _package, normalize_url
from src.run_batch import slugify


def test_normalize_url_adds_https():
    assert normalize_url("example.com") == "https://example.com"


def test_normalize_url_rejects_non_http_scheme():
    with pytest.raises(AuditError):
        normalize_url("file:///etc/passwd")


def test_grade_boundaries():
    assert _grade(95) == "A"
    assert _grade(84) == "B"
    assert _grade(74) == "C"
    assert _grade(64) == "D"
    assert _grade(40) == "F"


def test_package_tiers():
    assert _package(40)["name"] == "Full Digital Upgrade"
    assert _package(60)["name"] == "Complete Digital Refresh"
    assert _package(80)["name"] == "Digital Cleanup"


def test_slugify():
    assert slugify("My Great Business!") == "my-great-business"
