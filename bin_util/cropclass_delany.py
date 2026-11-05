"""Run Delany prediction postprocessing and identify multi-crop parcels."""

import logging
import math
from pathlib import Path

import geofileops as gfo

from datetime import datetime
import os
from osgeo import gdal

from cropclassification.postprocess.delany_postprocess import run

logger = logging.getLogger(__name__)


def main() -> None:
    # INIT
    parcel_prediction_path = Path("X:/Monitoring/Markers/dev/2026_CROPGROUP/Run_2026-10-22_001/Prc_BEFL_2026_2026-08-10_bufm5_weekly_predict_all.gpkg")
    delany_prediction_path = Path("X:/Monitoring/Markers/dev/2026_CROPGROUP/Run_2026-11-04_004/2026_s2_bufm5_weekly_predict_all.gpkg")
    min_delany_area_percentage = 20
    
    input_parcel_path = Path("X:/Monitoring/Markers/dev/_inputdata/2026_s2_reprojected.gpkg")
    input_parcel_simplified_path = Path("X:/Monitoring/Markers/dev/_inputdata_preprocessed/2026_s2_simplified.gpkg")
        

    # RUN
    try:
        with gdal.Run(
                "vector",
                "simplify-coverage",
                input=input_parcel_path,
                output=input_parcel_simplified_path,
                tolerance=3.0,
                # preserve_boundary=True,
            ) as alg:
                pass

        # run(
        #     parcel_prediction_path=parcel_prediction_path,
        #     delany_prediction_path=delany_prediction_path,
        #     min_delany_area_percentage=min_delany_area_percentage,
        # )
        logger.info("Script successfully executed.")
    except Exception as e:
        logger.error(f"Error executing script: {e}")

if __name__ == "__main__":
    main()
