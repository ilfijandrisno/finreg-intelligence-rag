"""Otoritas Jasa Keuangan (OJK) Peraturan OJK (POJK) Source Adapter."""

import logging
import re

from bs4 import Tag

from finreg.ingestion.adapters.base import (
    build_absolute_url,
    fetch_html_content,
    parse_html_document,
)
from finreg.ingestion.models import (
    DocumentReference,
    DocumentType,
    RegulationMetadata,
    RegulationReference,
)

logger = logging.getLogger(__name__)

OJK_BASE_URL = "https://www.ojk.go.id"
OJK_POJK_LISTING_URL = "https://www.ojk.go.id/id/regulasi/default.aspx"


class OjkAdapter:
    """Source adapter for Otoritas Jasa Keuangan (OJK) - Peraturan OJK (POJK)."""

    def __init__(self, listing_url: str = OJK_POJK_LISTING_URL):
        self.listing_url = listing_url

    @property
    def source_name(self) -> str:
        return "OJK"

    @property
    def target_regulation_type(self) -> str:
        return "POJK"

    def parse_listing_html(
        self, html_content: str, base_url: str = OJK_BASE_URL
    ) -> list[RegulationReference]:
        """Parse OJK regulation listing HTML into a list of RegulationReference objects."""
        soup = parse_html_document(html_content)
        results: list[RegulationReference] = []

        items = soup.select(".item, .item-title, td, li, a[href*='/regulasi/'], a[href*='POJK']")
        seen_urls: set[str] = set()

        for item in items:
            link_tag: Tag | None = None
            if item.name == "a" and "href" in item.attrs:
                link_tag = item
            else:
                found = item.find("a", href=True)
                if isinstance(found, Tag):
                    link_tag = found

            if not link_tag or not link_tag.get("href"):
                continue

            href = str(link_tag.get("href", "")).strip()
            if href.endswith(".pdf") or "pages" not in href.lower():
                continue

            detail_url = build_absolute_url(base_url, href)
            if detail_url in seen_urls:
                continue
            seen_urls.add(detail_url)

            title = link_tag.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            # Extract POJK number (e.g., 12/POJK.03/2020 or POJK Nomor 3/POJK.04/2021)
            num_match = re.search(r"(\d+/POJK\.\d+/\d{4}|\d+/POJK/\d{4})", title, re.IGNORECASE)
            reg_num = num_match.group(1) if num_match else "POJK-UNKNOWN"

            results.append(
                RegulationReference(
                    source="OJK",
                    regulation_type="POJK",
                    regulation_number=reg_num,
                    title=title,
                    detail_url=detail_url,
                )
            )

        return results

    def discover_regulations(self, limit: int | None = None) -> list[RegulationReference]:
        """Discover OJK POJK regulations from official listing page."""
        logger.info("Discovering OJK POJK regulations from %s", self.listing_url)
        try:
            html_content, final_url = fetch_html_content(self.listing_url)
            discovered = self.parse_listing_html(html_content, base_url=final_url)
        except Exception as exc:
            logger.error("Failed to fetch OJK listing page: %s", exc)
            discovered = []

        if limit and limit > 0:
            return discovered[:limit]
        return discovered

    def parse_detail_html(
        self, html_content: str, reference: RegulationReference
    ) -> tuple[RegulationMetadata, list[DocumentReference]]:
        """Parse OJK regulation detail HTML into RegulationMetadata and DocumentReferences."""
        soup = parse_html_document(html_content)

        # Extract title
        title_el = soup.find(["h1", "h2", "h3"], id=re.compile(r"title", re.I))
        title = title_el.get_text(strip=True) if title_el else reference.title

        meta_text = soup.get_text()
        status_match = re.search(r"Status\s*:\s*([^\n\r<]+)", meta_text, re.I)
        status = status_match.group(1).strip() if status_match else "Berlaku"

        sector_match = re.search(r"Sektor\s*:\s*([^\n\r<]+)", meta_text, re.I)
        sector = sector_match.group(1).strip() if sector_match else "Perbankan / Pasar Modal"

        # Summary / abstract
        summary_el = soup.find("div", class_=re.compile(r"content|description|body", re.I))
        summary = summary_el.get_text(strip=True)[:1000] if summary_el else None

        metadata = RegulationMetadata(
            source="OJK",
            regulation_type="POJK",
            regulation_number=reference.regulation_number,
            title=title,
            sector=sector,
            status=status,
            published_date=reference.published_date,
            detail_url=reference.detail_url,
            summary=summary,
        )

        # Resolve attachments
        documents: list[DocumentReference] = []
        pdf_links = soup.find_all("a", href=re.compile(r"\.pdf", re.I))
        seen_pdf_urls: set[str] = set()

        for link in pdf_links:
            if not isinstance(link, Tag) or not link.get("href"):
                continue
            pdf_href = str(link.get("href", "")).strip()
            pdf_url = build_absolute_url(reference.detail_url, pdf_href)
            if pdf_url in seen_pdf_urls:
                continue
            seen_pdf_urls.add(pdf_url)

            link_text = link.get_text(strip=True).lower()
            filename = pdf_url.split("/")[-1] or "pojk_document.pdf"

            doc_type = DocumentType.REGULATION
            if "faq" in link_text or "tanya" in link_text:
                doc_type = DocumentType.FAQ
            elif "abstrak" in link_text or "ringkasan" in link_text:
                doc_type = DocumentType.ABSTRACT
            elif "salinan" in link_text or "pojk" in link_text or "peraturan" in link_text:
                doc_type = DocumentType.REGULATION
            elif "lampiran" in link_text:
                doc_type = DocumentType.OTHER

            documents.append(
                DocumentReference(
                    document_type=doc_type,
                    url=pdf_url,
                    filename=filename,
                    content_type="application/pdf",
                )
            )

        metadata.attachments = documents
        return metadata, documents

    def fetch_metadata(self, reference: RegulationReference) -> RegulationMetadata:
        """Fetch and parse detailed metadata from official OJK detail page."""
        logger.info("Fetching OJK detail metadata from %s", reference.detail_url)
        html_content, _ = fetch_html_content(reference.detail_url)
        metadata, _ = self.parse_detail_html(html_content, reference)
        return metadata

    def resolve_documents(self, metadata: RegulationMetadata) -> list[DocumentReference]:
        """Return explicit attachment document references from resolved metadata."""
        return metadata.attachments
