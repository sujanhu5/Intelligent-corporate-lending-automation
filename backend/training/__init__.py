"""
Standalone training CLI for the Corporate Lending Automation ML pipeline.

Usage (from the backend/ directory):
    python -m training                          # train with defaults from .env + config
    python -m training --dry-run               # validate dataset and config, do not train
    python -m training --no-smote              # skip SMOTE oversampling
    python -m training --top-k 20              # select top 20 features instead of 30
    python -m training --models rf xgb         # train only specific models (lr / rf / xgb)
    python -m training --out models/           # override models output directory

This module can also be imported to run training programmatically:
    from training import run_training, validate_environment
    result = run_training()
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Bootstrap: ensure backend/ is on sys.path so imports resolve ─────────────
_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.config import BASE_DIR, settings
from app.core.logging import configure_logging, get_logger
from ml.dataset import load_feature_config
from ml.trainer import TrainingResult, models_are_trained, train_all

configure_logging()
logger = get_logger(__name__)

_DEFAULT_CONFIG_PATH = BASE_DIR / "config" / "feature_config.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_environment(
    dataset_path: Optional[Path] = None,
    config_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Validate that all prerequisites for training are present without actually
    training. Returns a dict describing what was found.

    Raises:
        SystemExit: if any critical prerequisite is missing.
    """
    dataset_path = dataset_path or settings.dataset_path
    config_path  = config_path  or _DEFAULT_CONFIG_PATH

    issues: List[str] = []
    report: Dict[str, Any] = {}

    # Dataset
    if not dataset_path.exists():
        issues.append(f"Dataset not found: {dataset_path}")
    else:
        import pandas as pd
        try:
            df = pd.read_csv(dataset_path, nrows=5)
            report["dataset"] = {
                "path": str(dataset_path),
                "columns_sample": list(df.columns[:10]),
            }
        except Exception as exc:
            issues.append(f"Dataset unreadable: {exc}")

    # Config
    if not config_path.exists():
        issues.append(f"Feature config not found: {config_path}")
    else:
        try:
            cfg = load_feature_config(config_path)
            report["config"] = {
                "path": str(config_path),
                "target_column": cfg.get("dataset", {}).get("target_column"),
                "top_k": cfg.get("feature_selection", {}).get("top_k"),
            }
        except Exception as exc:
            issues.append(f"Feature config unreadable: {exc}")

    # Models directory
    models_path = settings.models_path
    report["models_dir"] = str(models_path)
    report["already_trained"] = models_are_trained(models_path)

    if issues:
        for issue in issues:
            print(f"  ERROR  {issue}", file=sys.stderr)
        sys.exit(1)

    return report


def run_training(
    dataset_path: Optional[Path] = None,
    config_path: Optional[Path] = None,
    models_path: Optional[Path] = None,
    top_k: Optional[int] = None,
    apply_smote: bool = True,
    random_state: int = 42,
    test_size: float = 0.20,
    cv_folds: int = 5,
    model_subset: Optional[List[str]] = None,
) -> TrainingResult:
    """
    Run the full ML training pipeline and return the TrainingResult.

    Args:
        dataset_path:  Path to the CSV dataset (defaults to settings.dataset_path).
        config_path:   Path to feature_config.json (defaults to config/).
        models_path:   Directory where pkl files will be saved.
        top_k:         Override feature_config.json feature_selection.top_k.
        apply_smote:   Whether to apply SMOTE oversampling.
        random_state:  Seed for reproducibility.
        test_size:     Fraction of data reserved for the test set.
        cv_folds:      Number of cross-validation folds.
        model_subset:  If given, train only these models (lr / rf / xgb).

    Returns:
        TrainingResult dataclass with metrics for all trained models.
    """
    dataset_path = dataset_path or settings.dataset_path
    config_path  = config_path  or _DEFAULT_CONFIG_PATH
    models_path  = models_path  or settings.models_path

    # Apply overrides to the config before passing to train_all
    cfg = load_feature_config(config_path)
    if top_k is not None:
        cfg.setdefault("feature_selection", {})["top_k"] = top_k

    # If a model subset is requested, restrict the models section
    if model_subset:
        _KEY_MAP = {"lr": "logistic_regression", "rf": "random_forest", "xgb": "xgboost"}
        requested = {_KEY_MAP.get(m, m) for m in model_subset}
        cfg["models"] = {k: v for k, v in cfg.get("models", {}).items() if k in requested}
        if not cfg["models"]:
            print("ERROR: No matching models found. Valid options: lr, rf, xgb", file=sys.stderr)
            sys.exit(1)

    # Write the (possibly-overridden) config to a temp file so train_all can load it
    import tempfile, os
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(cfg, tmp)
        tmp_path = Path(tmp.name)

    try:
        result = train_all(
            dataset_path=dataset_path,
            feature_config_path=tmp_path,
            models_path=models_path,
            random_state=random_state,
            test_size=test_size,
            cv_folds=cv_folds,
            apply_smote_flag=apply_smote,
        )
    finally:
        os.unlink(tmp_path)

    return result


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m training",
        description="Train ML models for the Corporate Lending Automation system.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate environment only — do not actually train.",
    )
    parser.add_argument(
        "--no-smote", action="store_true",
        help="Skip SMOTE oversampling (use when class imbalance handling is not needed).",
    )
    parser.add_argument(
        "--top-k", type=int, default=None, metavar="K",
        help="Override the number of top features to select (default: from config).",
    )
    parser.add_argument(
        "--models", nargs="+", metavar="MODEL", default=None,
        choices=["lr", "rf", "xgb"],
        help="Train only specific models. Choices: lr (logistic), rf (random forest), xgb (XGBoost).",
    )
    parser.add_argument(
        "--random-state", type=int, default=42, metavar="SEED",
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--test-size", type=float, default=0.20, metavar="FRAC",
        help="Fraction of data to reserve for testing.",
    )
    parser.add_argument(
        "--cv-folds", type=int, default=5, metavar="N",
        help="Number of cross-validation folds.",
    )
    parser.add_argument(
        "--dataset", type=Path, default=None, metavar="PATH",
        help="Override the dataset path (default: DATASET_PATH from .env).",
    )
    parser.add_argument(
        "--config", type=Path, default=None, metavar="PATH",
        help="Override the feature config path (default: config/feature_config.json).",
    )
    parser.add_argument(
        "--out", type=Path, default=None, metavar="DIR",
        help="Override the models output directory (default: MODELS_DIR from .env).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)

    print()
    print("=" * 60)
    print("  Corporate Lending Automation — ML Training Pipeline")
    print("=" * 60)
    print(f"  Dataset : {args.dataset or settings.dataset_path}")
    print(f"  Config  : {args.config or _DEFAULT_CONFIG_PATH}")
    print(f"  Models  : {args.out or settings.models_path}")
    print(f"  SMOTE   : {'disabled' if args.no_smote else 'enabled'}")
    print(f"  Top-K   : {args.top_k or '(from config)'}")
    print(f"  CV folds: {args.cv_folds}")
    print()

    # ── Validate ──────────────────────────────────────────────────────────────
    print("Validating environment...")
    report = validate_environment(
        dataset_path=args.dataset,
        config_path=args.config,
    )
    print(f"  Dataset    : OK ({report.get('dataset', {}).get('path', '')})")
    print(f"  Config     : OK (target={report.get('config', {}).get('target_column')}, top_k={report.get('config', {}).get('top_k')})")
    print(f"  Models dir : {report.get('models_dir')}")
    if report.get("already_trained"):
        print("  [!] Models are already trained — they will be overwritten.")

    if args.dry_run:
        print()
        print("Dry-run complete. No training performed.")
        return 0

    # ── Train ─────────────────────────────────────────────────────────────────
    print()
    print("Starting training...")
    t0 = time.perf_counter()

    try:
        result = run_training(
            dataset_path=args.dataset,
            config_path=args.config,
            models_path=args.out,
            top_k=args.top_k,
            apply_smote=not args.no_smote,
            random_state=args.random_state,
            test_size=args.test_size,
            cv_folds=args.cv_folds,
            model_subset=args.models,
        )
    except Exception as exc:
        print(f"\nTraining FAILED: {exc}", file=sys.stderr)
        logger.exception("Training failed")
        return 1

    elapsed = time.perf_counter() - t0

    # ── Report ────────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"  Training complete in {elapsed:.1f}s")
    print(f"  Samples  : {result.total_samples} total | {result.train_samples} train | {result.test_samples} test")
    print(f"  Features : {len(result.selected_features)} selected | {result.dropped_correlated_count} correlated dropped")
    print(f"  SMOTE    : {'applied' if result.smote_applied else 'skipped'}")
    print()
    print("  Model Results:")
    header = f"    {'Model':<22} {'Acc':>6} {'Prec':>6} {'Rec':>6} {'F1':>6} {'ROC-AUC':>8} {'CV ± std':>16}"
    print(header)
    print("    " + "-" * (len(header) - 4))
    for model_name, metrics in result.models.items():
        marker = " ★" if model_name == result.best_model else "  "
        print(
            f"    {model_name:<22}{marker}"
            f" {metrics['accuracy']:>5.3f}"
            f" {metrics['precision']:>6.3f}"
            f" {metrics['recall']:>6.3f}"
            f" {metrics['f1']:>6.3f}"
            f" {metrics['roc_auc']:>8.4f}"
            f" {metrics['cv_roc_auc_mean']:.4f} ± {metrics['cv_roc_auc_std']:.4f}"
        )
    print()
    print(f"  Best model : {result.best_model} (ROC-AUC {result.best_roc_auc:.4f})")
    print("=" * 60)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
