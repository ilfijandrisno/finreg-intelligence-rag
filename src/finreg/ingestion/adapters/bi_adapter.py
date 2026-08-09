"""Bank Indonesia (BI) Peraturan Bank Indonesia (PBI) Source Adapter."""

import logging
import re
from datetime import date

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

BI_BASE_URL = "https://www.bi.go.id"
BI_PBI_LISTING_URL = "https://www.bi.go.id/id/publikasi/peraturan/default.aspx"


class BankIndonesiaAdapter:
    """Source adapter for Bank Indonesia (BI) - Peraturan Bank Indonesia (PBI)."""

    def __init__(self, listing_url: str = BI_PBI_LISTING_URL):
        self.listing_url = listing_url

    @property
    def source_name(self) -> str:
        return "BI"

    @property
    def target_regulation_type(self) -> str:
        return "PBI"

    def parse_listing_html(
        self, html_content: str, base_url: str = BI_BASE_URL
    ) -> list[RegulationReference]:
        """Parse BI regulation listing HTML into a list of RegulationReference objects."""
        soup = parse_html_document(html_content)
        results: list[RegulationReference] = []

        # Target BI publication listing items / table rows / card elements
        items = soup.select(
            ".bi-row-item, .table-row, tr, .publication-item, a[href*='/peraturan/']"
        )
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
            if "/peraturan/" not in href.lower() or href.endswith(".pdf"):
                continue

            if href.lower().endswith("/default.aspx") or href.lower().endswith("/peraturan/"):
                continue

            detail_url = build_absolute_url(base_url, href)
            if detail_url in seen_urls:
                continue

            title = link_tag.get_text(strip=True)
            if not title or len(title) < 5:
                continue

            seen_urls.add(detail_url)

            # Extract PBI number (e.g. 23/13/PBI/2021 or No. 24/1/PBI/2022)
            num_match = re.search(r"(\d+/\d+/PBI/\d{4}|\d+/PBI/\d{4})", title, re.IGNORECASE)
            reg_num = num_match.group(1) if num_match else "PBI-UNKNOWN"

            results.append(
                RegulationReference(
                    source="BI",
                    regulation_type="PBI",
                    regulation_number=reg_num,
                    title=title,
                    detail_url=detail_url,
                )
            )

        return results

    def discover_regulations(self, limit: int | None = None) -> list[RegulationReference]:
        """Discover BI PBI regulations from official listing page."""
        logger.info("Discovering BI PBI regulations from %s", self.listing_url)
        try:
            html_content, final_url = fetch_html_content(self.listing_url)
            discovered = self.parse_listing_html(html_content, base_url=final_url)
        except Exception as exc:
            logger.error("Failed to fetch BI listing page: %s", exc)
            discovered = []

        if limit and limit > 0:
            return discovered[:limit]
        return discovered

    def parse_detail_html(
        self, html_content: str, reference: RegulationReference
    ) -> tuple[RegulationMetadata, list[DocumentReference]]:
        """Parse BI regulation detail HTML into RegulationMetadata and DocumentReferences."""
        soup = parse_html_document(html_content)

        # Extract title
        title_el = soup.find(["h1", "h2", "h3"], class_=re.compile(r"title|header", re.I))
        title = title_el.get_text(strip=True) if title_el else reference.title

        # Extract metadata fields
        meta_text = soup.get_text()
        status_match = re.search(r"Status\s*:\s*([^\n\r<]+)", meta_text, re.I)
        status = status_match.group(1).strip() if status_match else "Berlaku"

        pub_date_match = re.search(
            r"Tanggal\s+Terbit\s*:\s*(\d{1,2}\s+\w+\s+\d{4})", meta_text, re.I
        )
        pub_date = (
            self._parse_indonesian_date(pub_date_match.group(1))
            if pub_date_match
            else reference.published_date
        )

        eff_date_match = re.search(
            r"Tanggal\s+Berlaku\s*:\s*(\d{1,2}\s+\w+\s+\d{4})", meta_text, re.I
        )
        eff_date = self._parse_indonesian_date(eff_date_match.group(1)) if eff_date_match else None

        # Extract summary / abstract
        summary_el = soup.find("div", class_=re.compile(r"summary|abstrak|content", re.I))
        summary = summary_el.get_text(strip=True)[:1000] if summary_el else None

        metadata = RegulationMetadata(
            source="BI",
            regulation_type="PBI",
            regulation_number=reference.regulation_number,
            title=title,
            sector="Moneter dan Sistem Pembayaran",
            status=status,
            published_date=pub_date,
            effective_date=eff_date,
            detail_url=reference.detail_url,
            summary=summary,
        )

        # Resolve document attachments
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
            filename = pdf_url.split("/")[-1] or "document.pdf"

            doc_type = DocumentType.REGULATION
            if "faq" in link_text or "tanya" in link_text:
                doc_type = DocumentType.FAQ
            elif "abstrak" in link_text or "ringkasan" in link_text:
                doc_type = DocumentType.ABSTRACT
            elif "lampiran" in link_text or "penjelasan" in link_text:
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
        """Fetch and parse detailed metadata from the official BI detail page."""
        logger.info("Fetching BI detail metadata from %s", reference.detail_url)
        html_content, _ = fetch_html_content(reference.detail_url)
        metadata, _ = self.parse_detail_html(html_content, reference)
        return metadata

    def resolve_documents(self, metadata: RegulationMetadata) -> list[DocumentReference]:
        """Return explicit attachment document references from resolved metadata."""
        return metadata.attachments

    def _parse_indonesian_date(self, date_str: str) -> date | None:
        """Helper to parse Indonesian date strings like '15 Desember 2021'."""
        months = {
            "januari": 1,
            "februari": 2,
            "maret": 3,
            "april": 4,
            "mei": 5,
            "juni": 6,
            "juli": 7,
            "agustus": 8,
            "september": 9,
            "oktober": 10,
            "november": 11,
            "desember": 12,
        }
        try:
            parts = date_str.strip().split()
            if len(parts) == 3:
                day = int(parts[0])
                month = months.get(parts[1].lower(), 1)
                year = int(parts[2])
                return date(year, month, day)
        except Exception:
            pass
        return None
