
# app/routers/settings.py
from fastapi import APIRouter
import dns.resolver
import time

from app.schemas.domain_status import DomainStatusResponse, DNSRecordDetail

router = APIRouter(prefix="/settings", tags=["settings"])

DOMAIN = "ibcb-a.com"
DKIM_SELECTOR = "google"

CACHE_TTL_SECONDS = 300  # 5 minutes
_cache_data = None
_cache_timestamp = 0

def check_spf(domain: str) -> str:
    try:
        txt_records = dns.resolver.resolve(domain, 'TXT')
        for r in txt_records:
            if "v=spf1" in str(r):
                return "Configured"
        return "Not configured"
    except Exception:
        return "Not configured"

def check_dkim(domain: str, selector: str) -> str:
    dkim_domain = f"{selector}._domainkey.{domain}"
    try:
        dns.resolver.resolve(dkim_domain, 'TXT')
        return "Configured"
    except Exception:
        return "Not configured"

def check_dmarc(domain: str) -> str:
    dmarc_domain = f"_dmarc.{domain}"
    try:
        dns.resolver.resolve(dmarc_domain, "TXT")
        return "Configured"
    except Exception:
        return "Not configured"

def compute_domain_status() -> DomainStatusResponse:
    spf_status = check_spf(DOMAIN)
    dkim_status = check_dkim(DOMAIN, DKIM_SELECTOR)
    dmarc_status = check_dmarc(DOMAIN)

    return DomainStatusResponse(
        domain=DOMAIN,
        records={
            "SPF": DNSRecordDetail(
                status=spf_status,
                expected="v=spf1 include:_spf.google.com ~all"
            ),
            "DKIM": DNSRecordDetail(
                status=dkim_status,
                selector=DKIM_SELECTOR
            ),
            "DMARC": DNSRecordDetail(
                status=dmarc_status,
                expected="v=DMARC1; p=none; rua=mailto:admin@ibcb-a.com"
            ),
        }
    )

def get_cached_domain_status() -> DomainStatusResponse:
    global _cache_data, _cache_timestamp
    now = time.time()
    if _cache_data is None or (now - _cache_timestamp) > CACHE_TTL_SECONDS:
        _cache_data = compute_domain_status()
        _cache_timestamp = now
    return _cache_data

@router.get("/domain-status", response_model=DomainStatusResponse)
def get_domain_status():
    return get_cached_domain_status()


