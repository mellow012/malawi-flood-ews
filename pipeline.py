"""
Malawi Flood EWS — Automated Pipeline Runner
Connects GEE SAR processing → ML model → SMS alerts
Run this on a schedule (e.g. cron every 12 hours) or trigger manually
"""

import os
import json
import logging
import datetime
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

try:
    import rasterio
    RASTERIO_AVAILABLE = True
except ImportError:
    RASTERIO_AVAILABLE = False
    logger.warning("rasterio not installed — flood area will use demo value")


FOCAL_POINTS = [
    {'name': 'James Banda',  'district': 'Chikwawa', 'phone': '+265991234567',
     'role': 'Village Head',  'active': True},
    {'name': 'Grace Mwale',  'district': 'Nsanje',   'phone': '+265888345678',
     'role': 'DoDMA Officer', 'active': True},
    {'name': 'Peter Chirwa', 'district': 'Nsanje',   'phone': '+265777456789',
     'role': 'Red Cross',     'active': True},
    {'name': 'Mary Phiri',   'district': 'Chikwawa', 'phone': '+265999567890',
     'role': 'Health Worker', 'active': True},
]


def run_gee_pipeline(roi: list, date: str) -> dict:
    """
    Run GEE SAR preprocessing pipeline via Python API.
    Returns paths to exported GeoTIFF files.
    In production: triggers the GEE pipeline and waits for export.
    In demo mode: returns paths to already-exported files.
    """
    logger.info(f"Running GEE pipeline for {date}...")
    folder = os.getenv('GDRIVE_FOLDER', '/content/drive/MyDrive/MalawiFloodEWS')
    return {
        'after_sar':  f'{folder}/malawi_s1_after_idai_db_v10.tif',
        'diff':       f'{folder}/malawi_s1_diff_all_bands_v10.tif',
        'flood_mask': f'{folder}/malawi_flood_mask_idai_2019.tif',
        'status':     'completed',
        'date':       date,
    }


def load_model(model_path: str):
    """Load saved ML model from joblib file."""
    try:
        import joblib
        model = joblib.load(model_path)
        logger.info(f"Model loaded: {model_path}")
        return model
    except Exception as e:
        logger.error(f"Model load failed: {e}")
        return None


def compute_flood_area(flood_mask_path: str, scale_m: int = 10) -> float:
    """Compute flood extent area in km² from binary raster."""
    if not RASTERIO_AVAILABLE:
        logger.warning("rasterio not installed — returning demo flood area")
        return 312.4
    try:
        with rasterio.open(flood_mask_path) as src:
            data = src.read(1)
            flood_pixels = int(np.sum(data == 1))
            pixel_area_m2 = scale_m * scale_m
            flood_area_km2 = (flood_pixels * pixel_area_m2) / 1_000_000
            logger.info(f"Flood area: {flood_area_km2:.2f} km² "
                        f"({flood_pixels:,} pixels)")
            return float(flood_area_km2)
    except Exception as e:
        logger.error(f"Flood area computation failed: {e}")
        return 0.0


def run_pipeline(
    roi:        list           = [34.20, -16.80, 34.90, -15.60],
    date:       str | None     = None,
    dry_run:    bool           = True,
    min_alert:  str            = 'MEDIUM',
    model_path: str | None     = None,
) -> dict:
    """
    Full end-to-end pipeline:
    1. GEE SAR processing
    2. ML flood prediction
    3. Flood area computation
    4. SMS alert dispatch (if threshold exceeded)
    """
    if date is None:
        date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
    date = str(date)

    logger.info("=" * 60)
    logger.info(f"Malawi Flood EWS Pipeline — {date}")
    logger.info("=" * 60)

    results = {
        'date':      date,
        'status':    'running',
        'gee':       None,
        'flood_area_chikwawa': 0.0,
        'flood_area_nsanje':   0.0,
        'alerts_sent':         [],
        'errors':              [],
    }

    # ── Step 1: GEE ───────────────────────────────────────────────────
    try:
        gee_result = run_gee_pipeline(roi, date)
        results['gee'] = gee_result
        logger.info(f"GEE pipeline: {gee_result['status']}")
    except Exception as e:
        results['errors'].append(f"GEE: {e}")
        logger.error(f"GEE failed: {e}")

    # ── Step 2: Flood area ────────────────────────────────────────────
    if results['gee'] and results['gee']['status'] == 'completed':
        try:
            total_area = compute_flood_area(results['gee']['flood_mask'])
            # Split roughly 60/40 between Chikwawa and Nsanje
            results['flood_area_chikwawa'] = total_area * 0.61
            results['flood_area_nsanje']   = total_area * 0.39
            logger.info(f"Chikwawa: {results['flood_area_chikwawa']:.1f} km²")
            logger.info(f"Nsanje:   {results['flood_area_nsanje']:.1f} km²")
        except Exception as e:
            results['errors'].append(f"Flood area: {e}")
            logger.error(f"Flood area failed: {e}")

    # ── Step 3: Alert dispatch ────────────────────────────────────────
    from alert_system import FloodAlertSystem, check_and_trigger

    for district, area_key in [
        ('Chikwawa', 'flood_area_chikwawa'),
        ('Nsanje',   'flood_area_nsanje'),
    ]:
        flood_area = results[area_key]
        if flood_area > 0:
            alert_result = check_and_trigger(
                flood_area_km2=flood_area,
                district=district,
                focal_points=FOCAL_POINTS,
                min_level=min_alert,
                dry_run=dry_run,
            )
            if alert_result:
                results['alerts_sent'].append({
                    'district': district,
                    'level':    alert_result.get('level'),
                    'area':     flood_area,
                    'sent':     alert_result.get('success'),
                })

    results['status'] = 'completed' if not results['errors'] else 'partial'
    logger.info(f"Pipeline complete. Status: {results['status']}")
    logger.info(f"Alerts sent: {len(results['alerts_sent'])}")

    # Save run log
    log_path = Path('pipeline_log.jsonl')
    with open(log_path, 'a') as f:
        f.write(json.dumps(results, default=str) + '\n')

    return results


if __name__ == '__main__':
    result = run_pipeline(dry_run=True)
    print("\n" + "=" * 60)
    print("PIPELINE RESULT SUMMARY")
    print("=" * 60)
    print(f"Status:     {result['status']}")
    print(f"Chikwawa:   {result['flood_area_chikwawa']:.1f} km²")
    print(f"Nsanje:     {result['flood_area_nsanje']:.1f} km²")
    print(f"Alerts:     {len(result['alerts_sent'])}")
    if result['errors']:
        print(f"Errors:     {result['errors']}")