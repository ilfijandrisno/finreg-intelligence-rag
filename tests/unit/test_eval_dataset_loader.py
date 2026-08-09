"""Unit tests for dataset loader and canonical evidence keys."""

from pathlib import Path
from uuid import uuid4

import pytest

from finreg.evaluation.dataset_loader import load_eval_dataset, save_eval_dataset
from finreg.evaluation.eval_models import CanonicalEvidence, EvalDataset, EvalSample


def test_canonical_evidence_key() -> None:
    doc_id = uuid4()
    ev = CanonicalEvidence(
        document_id=doc_id,
        structural_path="BAB I/Pasal 1",
        page_start=2,
        page_end=3,
        relevance=3,
    )
    expected_key = f"{doc_id}:BAB I/Pasal 1:2:3"
    assert ev.to_canonical_key() == expected_key


def test_dataset_loader(tmp_path: Path) -> None:
    ds_file = tmp_path / "test_ds.json"
    doc_id = uuid4()
    ev = CanonicalEvidence(
        document_id=doc_id, structural_path="Pasal 1", page_start=1, page_end=1, relevance=3
    )
    sample = EvalSample(sample_id="s1", query="test query", canonical_ground_truth=[ev])
    ds = EvalDataset(dataset_version="1.0.0", samples=[sample])

    save_eval_dataset(ds, ds_file)
    assert ds_file.exists()

    loaded = load_eval_dataset(ds_file)
    assert loaded.dataset_version == "1.0.0"
    assert len(loaded.samples) == 1
    assert loaded.samples[0].query == "test query"


def test_dataset_loader_invalid_file(tmp_path: Path) -> None:
    non_existent = tmp_path / "non_existent.json"
    with pytest.raises(FileNotFoundError):
        load_eval_dataset(non_existent)
