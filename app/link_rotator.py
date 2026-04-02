from __future__ import annotations

import random
import re
# from urllib.parse import quote

from sqlalchemy.orm import Session

from .models import Campaign, ClickEvent, Link, LinkVariant


ANCHOR_PATTERN = re.compile(
    r'<a\s+([^>]*?)href=["\']([^"\']+)["\']([^>]*)>',
    flags=re.IGNORECASE,
)


def ensure_link_and_variants(
    db: Session,
    campaign_id: int,
    url: str,
    label: str | None = None,
) -> Link:
    existing = (
        db.query(Link)
        .filter(
            Link.campaign_id == campaign_id,
            Link.original_url == url,
        )
        .first()
    )
    if existing:
        has_variant = (
            db.query(LinkVariant)
            .filter(LinkVariant.link_id == existing.id)
            .first()
        )
        if not has_variant:
            db.add(
                LinkVariant(
                    link_id=existing.id,
                    url=url,
                    weight=100,
                    is_active=True,
                )
            )
            db.commit()
        return existing

    link = Link(
        campaign_id=campaign_id,
        label=label,
        original_url=url,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    variant = LinkVariant(
        link_id=link.id,
        url=url,
        weight=100,
        is_active=True,
    )
    db.add(variant)
    db.commit()
    db.refresh(link)

    return link


def replace_links_for_contact(
    db: Session,
    campaign: Campaign,
    html: str,
    contact_id: int | None = None,
    base_tracking_url: str = "http://localhost:8000",
) -> str:
    def _replace(match: re.Match) -> str:
        before_attrs = match.group(1) or ""
        original_url = match.group(2)
        after_attrs = match.group(3) or ""

        if original_url.startswith(("mailto:", "tel:", "#", "javascript:")):
            return match.group(0)

        link = ensure_link_and_variants(
            db=db,
            campaign_id=campaign.id,
            url=original_url,
            label=None,
        )

        track_url = f"{base_tracking_url}/r/{link.id}"
        if contact_id:
            track_url += f"?contact_id={contact_id}"

        return f'<a {before_attrs}href="{track_url}"{after_attrs}>'

    return ANCHOR_PATTERN.sub(_replace, html)


def choose_variant(db: Session, link_id: int) -> LinkVariant | None:
    variants = (
        db.query(LinkVariant)
        .filter(
            LinkVariant.link_id == link_id,
            LinkVariant.is_active == True,  # noqa: E712
        )
        .all()
    )
    if not variants:
        return None

    population = []
    for variant in variants:
        weight = max(int(variant.weight or 0), 0)
        if weight > 0:
            population.extend([variant] * weight)

    if not population:
        return variants[0]

    return random.choice(population)


def register_click(
    db: Session,
    campaign_id: int,
    contact_id: int | None,
    link_id: int,
    variant_id: int | None,
    ip_address: str | None,
    user_agent: str | None,
) -> ClickEvent:
    event = ClickEvent(
        campaign_id=campaign_id,
        contact_id=contact_id,
        link_id=link_id,
        variant_id=variant_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event



