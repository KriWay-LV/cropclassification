"""Run Delany prediction postprocessing and identify multi-crop parcels."""

import logging
import math
from pathlib import Path

import geofileops as gfo

from datetime import datetime
import os
from osgeo import gdal

from cropclassification.postprocess.delany_postprocess import run
import pyproj

logger = logging.getLogger(__name__)

def x_dir() -> Path:
    if os.name == "nt":
        return Path("X:/")
    else:
        return Path("/mnt/shared/Common")

def main() -> None:
    # INIT
    simplify_tolerance = 10
    negative_buffer_distance = 5
    minimum_parcel_area = 10
    parcel_prediction_path = x_dir() / "Monitoring/Markers/dev/2026_CROPGROUP/Run_2026-10-22_001/Prc_BEFL_2026_2026-08-10_bufm5_weekly_predict_all.gpkg"
    delany_prediction_path = x_dir() / f"Monitoring/Markers/dev/2026_CROPGROUP/Run_2026-11-18_001/2026_s2_bufm5_weekly_predict_all.gpkg"

    # RUN
    try:
        run(
            parcel_prediction_path=parcel_prediction_path,
            delany_prediction_path=delany_prediction_path,
            simplify_tolerance=simplify_tolerance,
            negative_buffer_distance=negative_buffer_distance,
            minimum_parcel_area=minimum_parcel_area,
        )
        logger.info("Script successfully executed.")
    except Exception as e:
        logger.error(f"Error executing script: {e}")

if __name__ == "__main__":
    main()
