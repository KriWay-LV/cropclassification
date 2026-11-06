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
    parcel_prediction_path = x_dir() / "Monitoring/Markers/dev/2026_CROPGROUP/Run_2026-10-22_001/Prc_BEFL_2026_2026-08-10_bufm5_weekly_predict_all.gpkg"
    delany_prediction_path = x_dir() / "Monitoring/Markers/dev/2026_CROPGROUP/Run_2026-11-04_004/2026_s2_bufm5_weekly_predict_all.gpkg"
    min_delany_area_percentage = 20
    tolerance = 7.5
    distance = 5.0
    
    input_parcel_path = x_dir() / "Monitoring/Markers/dev/_inputdata/2026_s2.gpkg"
    output_dir = x_dir() / "Monitoring/Markers/dev/_inputdata_preprocessed"
    input_parcel_reprojected_path = output_dir / f"{input_parcel_path.stem}_reprojected{input_parcel_path.suffix}"
    input_parcel_simplified_path = output_dir / f"{input_parcel_path.stem}_simplified_{tolerance}{input_parcel_path.suffix}"
    input_parcel_buffered_path = (
        output_dir / f"{input_parcel_path.stem}_simplified_{tolerance}_bufm{distance}{input_parcel_path.suffix}"
    )

    # input_parcel_path = x_dir() / "Monitoring/Markers/dev/_inputdata/2026_s2.gpkg"
    # output_dir = x_dir() / "Monitoring/Markers/dev/_inputdata_preprocessed"
    # input_parcel_reprojected_path = output_dir / f"{input_parcel_path.stem}_simplified_5.0{input_parcel_path.suffix}"
    # input_parcel_simplified_path = output_dir / f"{input_parcel_path.stem}_simplified_5.0_{tolerance}{input_parcel_path.suffix}"


    # RUN
    try:
        # with gdal.Run(
        #         "vector",
        #         "simplify-coverage",
        #         input=input_parcel_path,
        #         output=input_parcel_simplified_path,
        #         tolerance=tolerance,
        #         # preserve_boundary=True,
        #     ) as alg:
        #         pass

        # info = gfo.get_layerinfo(input_parcel_path)
        # gfo.copy_layer(
        #     src=input_parcel_path,
        #     dst=input_parcel_reprojected_path,
        #     dst_crs="EPSG:31370",
        #     reproject=True,
        #     force=False,
        # )

        with gdal.alg.vector.simplify_coverage(
            input=input_parcel_reprojected_path,
            output=input_parcel_simplified_path,
            tolerance=tolerance,
            overwrite=True,
        ):
            pass

        gfo.buffer(
            input_path=input_parcel_simplified_path,
            output_path=input_parcel_buffered_path,
            distance=-distance,
            force=True,
        )

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
