# Data Governance & Regulatory Source Directory

**Language:** 🇬🇧 English · [🇮🇩 Bahasa Indonesia](README.id.md)

This directory serves as the root location for local regulatory dataset storage and metadata manifests.

### Data Governance Principles
1. **Official Sources Only**: All regulatory texts are sourced exclusively from official public regulatory portals:
   - **Bank Indonesia (BI)**: [https://www.bi.go.id](https://www.bi.go.id)
   - **Otoritas Jasa Keuangan (OJK)**: [https://www.ojk.go.id](https://www.ojk.go.id)
2. **Zero PDF Commit Policy**: Binary PDF files of financial regulations are **never** committed to Git repositories. They are maintained in local storage or object storage (S3/GCS).
3. **Traceability**: Raw and parsed regulatory documents retain full lineage, including original source URL, SHA-256 checksum, HTTP fetch timestamp, and issuing authority.
4. **Public Domain Compliance**: Content ingested consists solely of public regulatory acts, regulations, circular letters, and official guidance published for public compliance.
