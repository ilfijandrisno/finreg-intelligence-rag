"""Dataset loader and validator for benchmark evaluation datasets."""

from pathlib import Path

from finreg.evaluation.eval_models import EvalDataset


def load_eval_dataset(dataset_path: str | Path) -> EvalDataset:
    """Load and validate benchmark evaluation dataset from JSON file.

    Args:
        dataset_path: Path to benchmark dataset JSON file.

    Returns:
        EvalDataset: Validated Pydantic evaluation dataset object.

    Raises:
        FileNotFoundError: If dataset path does not exist.
        ValueError: If dataset JSON is invalid or empty.
    """
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset file not found at '{path}'")

    content = path.read_text(encoding="utf-8")
    try:
        dataset = EvalDataset.model_validate_json(content)
    except Exception as exc:
        raise ValueError(f"Failed to parse evaluation dataset at '{path}': {exc}") from exc

    if not dataset.samples:
        raise ValueError(f"Evaluation dataset at '{path}' contains zero samples")

    return dataset


def save_eval_dataset(dataset: EvalDataset, dataset_path: str | Path) -> None:
    """Save evaluation dataset to formatted JSON file."""
    path = Path(dataset_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    json_data = dataset.model_dump_json(indent=2)
    path.write_text(json_data, encoding="utf-8")
