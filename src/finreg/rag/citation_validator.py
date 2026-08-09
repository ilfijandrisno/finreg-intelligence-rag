"""Citation validation component enforcing strict provenance verification."""

import logging
import re
from collections.abc import Sequence

from finreg.rag.rag_models import ContextBlock, LegalCitation

logger = logging.getLogger(__name__)

# Regex pattern matching context tags like [C1], [C2], [C99]
CITATION_REGEX = re.compile(r"\[(C\d+)\]")


class CitationValidator:
    """Validates generated text citations against assigned context blocks."""

    def validate(
        self,
        text: str,
        context_blocks: Sequence[ContextBlock],
    ) -> tuple[bool, list[LegalCitation], list[str]]:
        """Extract citations and verify all cited context IDs against valid assigned blocks.

        Returns:
            tuple[bool, list[LegalCitation], list[str]]:
                - is_valid (bool): True if all cited context IDs are valid.
                - valid_citations (list[LegalCitation]): Validated LegalCitation objects list.
                - invalid_citations (list[str]): List of invalid context ID tags detected.
        """
        if not text or not text.strip():
            return True, [], []

        valid_map = {b.context_id: b for b in context_blocks}
        cited_tags = CITATION_REGEX.findall(text)

        valid_citations: list[LegalCitation] = []
        invalid_citations: list[str] = []
        seen_valid_ids: set[str] = set()

        for tag in cited_tags:
            if tag in valid_map:
                if tag not in seen_valid_ids:
                    seen_valid_ids.add(tag)
                    block = valid_map[tag]
                    res = block.reranked_result
                    cit = LegalCitation(
                        context_id=tag,
                        chunk_id=res.chunk_id,
                        source=res.source,
                        regulation_type=res.regulation_type,
                        regulation_number=res.regulation_number,
                        structural_path=res.structural_path,
                        page_start=res.page_start,
                        page_end=res.page_end,
                    )
                    valid_citations.append(cit)
            else:
                logger.warning("Citation validation failure: invalid context ID '[%s]'.", tag)
                if tag not in invalid_citations:
                    invalid_citations.append(tag)

        # STRICT SAFETY RULE: Any invalid citation tag causes validation failure (is_valid = False)
        is_valid = len(invalid_citations) == 0
        return is_valid, valid_citations, invalid_citations
