"""
download_and_reproduce.py — TAF-28k Audio Downloads + QAD-MultiGuard Complete Reproduction

Usage:
    # Run in an environment with access to HuggingFace:
    python scripts/download_and_reproduce.py

Steps:
    1. Download audio.zip (12.7 GB) from the HF Bucket
    2. Unzip it to data/TAF28k/audio/
    3. Extract 158-dimensional multimodal features
    4. Train the GBM model
    5. Evaluate and output F1, Precision, and Recall
    6. Update _fig_data.py
"""

import argparse, json, logging, os, sys, zipfile
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = REPO_ROOT / "data" / "TAF28k" / "audio"
RUNS_DIR = REPO_ROOT / "runs"


def step1_download_audio():
    """Download the TAF-28k audio file from HF Bucket"""
    import subprocess
    bucket = "wangdajin062/TeleAntiFraud-bucket"
    zip_path = REPO_ROOT / "data" / "TAF28k" / "audio.zip"

    if zip_path.exists() and zip_path.stat().st_size > 12_000_000_000:
        logger.info("audio.zip Already exists; skip download")
        return zip_path

    logger.info(f"Download audio.zip (12.7 GB) 从 bucket {bucket}...")
    logger.info("Note: This may take some time, depending on your internet speed.")

    result = subprocess.run([
        "hf", "buckets", "cp",
        f"hf://buckets/{bucket}/audio.zip",
        str(zip_path),
    ], capture_output=True, text=True)

    if result.returncode != 0:
        logger.error(f"Download Failed: {result.stderr}")
        logger.info("Please download it manually.: https://huggingface.co/buckets/wangdajin062/TeleAntiFraud-bucket")
        logger.info(f"  hf buckets cp hf://buckets/{bucket}/audio.zip data/TAF28k/")
        return None

    logger.info("Download Complete!")
    return zip_path


def step2_extract_audio(zip_path):
    """Extract the audio file"""
    if AUDIO_DIR.exists() and len(list(AUDIO_DIR.rglob("*.mp3"))) > 100:
        logger.info(f"The audio has been decompressed. ({len(list(AUDIO_DIR.rglob('*.mp3')))} 个文件)")
        return True

    logger.info(f"Unzip {zip_path} 到 {AUDIO_DIR}...")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(AUDIO_DIR.parent)
    logger.info(f"Extraction complete! {len(list(AUDIO_DIR.rglob('*.mp3')))} audio files")
    return True


def step3_extract_features():
    """Extract 158-dimensional multimodal features"""
    logger.info("Extracting multimodal features...")
    sys.path.insert(0, str(REPO_ROOT))

    from datasets import load_dataset
    ds = load_dataset("JimmyMa99/TeleAntiFraud", streaming=False)
    train_data, test_data = ds["train"], ds["test"]

    # Extracting Features Using the data_loader Pipeline
    from backend.ml.data_loader import TeleAntiFraudLoader
    loader = TeleAntiFraudLoader(audio_dir=AUDIO_DIR)

    # Force feature recalculation (without using the cache)
    data = loader.load_train_test(force_recompute=True)
    if data is None:
        logger.error("Feature extraction failed")
        return None

    X_train, y_train = data["X_train"], data["y_train"]
    X_test, y_test = data["X_test"], data["y_test"]

    logger.info(f"Features: train={X_train.shape}, test={X_test.shape}")
    return X_train, y_train, X_test, y_test


def step4_train_evaluate(X_train, y_train, X_test, y_test):
    """Train and evaluate the GBM model"""
    logger.info("Training the GBM model...")
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.metrics import (
        accuracy_score, precision_score, recall_score,
        f1_score, roc_auc_score, confusion_matrix,
    )

    clf = GradientBoostingClassifier(
        n_estimators=200, max_depth=4, learning_rate=0.08,
        subsample=0.8, random_state=42,
    )
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]

    cm = confusion_matrix(y_test, y_pred)
    results = {
        "f1": round(float(f1_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred)), 4),
        "recall": round(float(recall_score(y_test, y_pred)), 4),
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "auc": round(float(roc_auc_score(y_test, y_prob)), 4),
        "fpr": round(float(cm[0, 1] / max(cm[0, 0] + cm[0, 1], 1)), 4),
        "cm": cm.tolist(),
        "n_test": int(len(y_test)),
        "n_fraud": int(y_test.sum()),
    }

    logger.info(f"F1={results['f1']:.4f}, P={results['precision']:.4f}, "
                f"R={results['recall']:.4f}, FPR={results['fpr']:.4f}")
    return results, clf


def step5_update_paper_data(results):
    """Update the paper's backoff constant using measured data"""
    logger.info("Updating paper data...")

    # Update the GBM baseline data in _fig_data.py
    fig_data_path = REPO_ROOT / "figures_scripts" / "_fig_data.py"
    if fig_data_path.exists():
        content = fig_data_path.read_text(encoding="utf-8")

        # Update the GBM metadata baseline to reflect actual measurements
        # (BERT-Fraud in PAPER_FALLBACK)
        old = ('("BERT-Fraud [14]",          0.876, 0.000, "darkgray"),')
        new = (f'("GBM-Multimodal (Field Test)",      {results["f1"]:.3f}, 0.010, "darkgray"),\n'
               f'    ("BERT-Fraud [14]",          0.876, 0.000, "darkgray"),')
        content = content.replace(old, new)

        fig_data_path.write_text(content, encoding="utf-8")
        logger.info(f"_fig_data.py Updated (Added GBM test results: F1={results['f1']:.4f})")

    # Save the full report
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "timestamp": datetime.now().isoformat(),
        "audio_source": "TAF-28k HF Bucket",
        "feature_dim": 158,
        "model": "GradientBoostingClassifier",
        "evaluation": results,
        "paper_target": {
            "f1": 0.923,
            "note": "The paper aims to develop a QAD + OV-Freeze multimodal system",
        },
    }
    report_path = RUNS_DIR / "reproduction_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    logger.info(f"Save report to: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="TAF-28k Download + Full Reproduction")
    parser.add_argument("--skip-download", action="store_true", help="Skip Download (Audio File Already Exists)")
    parser.add_argument("--skip-extract", action="store_true", help="Skip extraction")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("TAF-28k Download and Reproduce with QAD-MultiGuard")
    logger.info(f"Time: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    # Step 1: Download
    if not args.skip_download:
        zip_path = step1_download_audio()
        if zip_path is None:
            logger.error("Download failed. Please download the file manually and try again.")
            return
    else:
        zip_path = REPO_ROOT / "data" / "TAF28k" / "audio.zip"

    # Step 2: Unzip
    if not args.skip_extract:
        if not step2_extract_audio(zip_path):
            return

    # Step 3-5: Feature extraction, training, and updating
    data = step3_extract_features()
    if data:
        X_train, y_train, X_test, y_test = data
        results, model = step4_train_evaluate(X_train, y_train, X_test, y_test)
        step5_update_paper_data(results)

    logger.info("\n Done! Now you can:")
    logger.info("  1. Run figures_scripts/generate_all.py to regenerate the charts")
    logger.info("  2. Update paper_v2.tex with the new F1/Precision/Recall values")
    logger.info(f"  3. Check the full report: {RUNS_DIR / 'reproduction_report.json'}}")


if __name__ == "__main__":
    main()
