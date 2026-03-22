"""
Malawi Flood EWS — Phase 5b: Automated Inference Pipeline
"""

import os
import json
import datetime
import numpy as np
import joblib
import glob
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

try:
    import rasterio
    from rasterio.enums import Resampling
    RASTERIO_OK = True
except ImportError:
    RASTERIO_OK = False

FOLDER      = os.getenv('GDRIVE_FOLDER',
              '/content/drive/MyDrive/MalawiFloodEWS')
RESULTS_LOG = 'flood_detection_log.jsonl'

ALERT_THRESHOLDS = {'CRITICAL':300,'HIGH':150,'MEDIUM':100,'LOW':50}

# Focal points defined here — no cross-module import needed
FOCAL_POINTS: list[dict] = [
    {'name':'James Banda', 'district':'Chikwawa',
     'phone':'+265991234567','role':'Village Head', 'active':True},
    {'name':'Grace Mwale', 'district':'Nsanje',
     'phone':'+265888345678','role':'DoDMA Officer','active':True},
    {'name':'Peter Chirwa','district':'Nsanje',
     'phone':'+265777456789','role':'Red Cross',    'active':True},
    {'name':'Mary Phiri',  'district':'Chikwawa',
     'phone':'+265999567890','role':'Health Worker','active':True},
]


def find_latest_exports(folder: str,
                        today: Optional[str] = None) -> dict[str, str]:
    if today is None:
        today = datetime.datetime.utcnow().strftime('%Y%m%d')
    tag   = f'auto_{today}'
    files: dict[str, str] = {}
    for key, pattern in [
        ('flood_mask', f'flood_mask_{tag}.tif'),
        ('sar_after',  f'sar_after_{tag}.tif'),
        ('sar_diff',   f'sar_diff_{tag}.tif'),
        ('rain',       f'chirps_rain_{tag}.tif'),
        ('terrain',    'malawi_terrain_features.tif'),
    ]:
        path = os.path.join(folder, pattern)
        if os.path.exists(path):
            files[key] = path
        else:
            matches = sorted(glob.glob(
                os.path.join(folder, f'*{key.replace("_","*")}*.tif')))
            if matches:
                files[key] = matches[-1]
    return files


def extract_features(
    files: dict[str, str],
    n_sample: int = 50000
) -> tuple[np.ndarray, np.ndarray, np.ndarray,
           tuple[int, int], np.ndarray]:
    if not RASTERIO_OK:
        raise RuntimeError("rasterio required")
    with rasterio.open(files['flood_mask']) as src:
        ref_shape: tuple[int, int] = (src.height, src.width)
        labels = src.read(1).astype(np.float32).ravel()
    np.random.seed(42)
    total      = ref_shape[0] * ref_shape[1]
    sample_idx = np.random.choice(total, min(n_sample, total), replace=False)
    rows = (sample_idx // ref_shape[1]).astype(np.int32)
    cols = (sample_idx %  ref_shape[1]).astype(np.int32)

    def read_bands(path: str, names: list[str]) -> list[np.ndarray]:
        out: list[np.ndarray] = []
        with rasterio.open(path) as src:
            for i in range(1, len(names) + 1):
                b = src.read(i, out_shape=ref_shape,
                             resampling=Resampling.bilinear
                             ).astype(np.float32)
                out.append(b[rows, cols]); del b
        return out

    sar  = read_bands(files['sar_after'], ['VV_db','VH_db'])
    diff = read_bands(files['sar_diff'],
                      ['diff_VV','diff_VH','diff_combined'])
    rain = read_bands(files['rain'],
                      ['rain_3d','rain_7d','rain_30d','rain_event','rain_peak'])
    terr = read_bands(files['terrain'],
                      ['elevation','slope','aspect','TWI','dist_to_water'])
    X = np.column_stack(sar + diff + rain + terr)
    return X, rows, cols, ref_shape, labels[sample_idx]


def load_models(folder: str) -> tuple:
    rf      = joblib.load(os.path.join(folder, 'model_rf_phase3b.pkl'))
    xgb     = joblib.load(os.path.join(folder, 'model_xgb_phase3b.pkl'))
    scaler  = joblib.load(os.path.join(folder, 'scaler_phase3b.pkl'))
    imputer = joblib.load(os.path.join(folder, 'imputer_phase3b.pkl'))
    return rf, xgb, scaler, imputer


def run_inference(X: np.ndarray, rf, xgb, scaler, imputer,
                  threshold: float = 0.5
                  ) -> tuple[np.ndarray, np.ndarray]:
    X_imp     = imputer.transform(X)
    X_sc      = scaler.transform(X_imp)
    ens_probs = (rf.predict_proba(X_imp)[:, 1] +
                 xgb.predict_proba(X_sc)[:, 1]) / 2
    preds     = (ens_probs > threshold).astype(np.int32)
    return ens_probs, preds


def estimate_flood_area(path: str, scale_m: int = 10) -> float:
    if not RASTERIO_OK:
        return 0.0
    with rasterio.open(path) as src:
        pixels = int(np.sum(src.read(1) == 1))
    return (pixels * scale_m * scale_m) / 1_000_000


def determine_alert_level(area_km2: float) -> str:
    for level in ('CRITICAL','HIGH','MEDIUM','LOW'):
        if area_km2 >= ALERT_THRESHOLDS[level]:
            return level
    return 'NONE'


def log_result(result: dict) -> None:
    with open(RESULTS_LOG, 'a') as f:
        f.write(json.dumps(result, default=str) + '\n')


def run_auto_pipeline(folder: str = FOLDER,
                      threshold: float = 0.5,
                      dry_run: bool = True) -> dict:
    today = datetime.datetime.utcnow().strftime('%Y%m%d')
    logger.info(f"Malawi Flood EWS Pipeline — {today}")

    result: dict = {
        'run_date': today, 'status': 'running',
        'flood_area': 0.0, 'alert_level': 'NONE',
        'threshold': threshold, 'errors': [], 'sms_sent': False,
    }

    files = find_latest_exports(folder, today)

    if 'flood_mask' in files:
        result['flood_area'] = estimate_flood_area(files['flood_mask'])
        logger.info(f"Flood area: {result['flood_area']:.2f} km²")

    if all(k in files for k in ['sar_after','sar_diff','rain','terrain']):
        try:
            rf, xgb, scaler, imputer = load_models(folder)
            X, *_ = extract_features(files)
            ens_probs, preds = run_inference(
                X, rf, xgb, scaler, imputer, threshold)
            result['ml_flood_fraction'] = float(np.mean(preds))
            result['ml_mean_prob']      = float(np.mean(ens_probs))
        except Exception as e:
            result['errors'].append(f"ML: {e}")
            logger.error(e)

    result['alert_level'] = determine_alert_level(result['flood_area'])
    logger.info(f"Alert level: {result['alert_level']}")

    if result['alert_level'] != 'NONE' and not dry_run:
        try:
            from alert_system import check_and_trigger
            for district in ['Chikwawa','Nsanje']:
                check_and_trigger(
                    flood_area_km2=result['flood_area'] * 0.6,
                    district=district,
                    focal_points=FOCAL_POINTS,
                    min_level='MEDIUM',
                    dry_run=dry_run
                )
            result['sms_sent'] = True
        except Exception as e:
            result['errors'].append(f"SMS: {e}")

    result['status'] = 'completed' if not result['errors'] else 'partial'
    log_result(result)
    return result


def start_scheduler(interval_hours: int = 12) -> None:
    import time
    while True:
        try:
            run_auto_pipeline(dry_run=False)
        except Exception as e:
            logger.error(e)
        time.sleep(interval_hours * 3600)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--schedule',  action='store_true')
    parser.add_argument('--dry-run',   action='store_true', default=True)
    parser.add_argument('--threshold', type=float, default=0.5)
    parser.add_argument('--folder',    type=str, default=FOLDER)
    args = parser.parse_args()
    if args.schedule:
        start_scheduler()
    else:
        result = run_auto_pipeline(args.folder, args.threshold, args.dry_run)
        print(json.dumps(result, indent=2, default=str))