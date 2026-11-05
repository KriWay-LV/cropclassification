"""Run Delany prediction postprocessing and identify multi-crop parcels."""

import logging
import math
from pathlib import Path

import geofileops as gfo

# Get a logger...
logger = logging.getLogger(__name__)


def run(
    parcel_prediction_path: Path,
    delany_prediction_path: Path,
    min_delany_area_percentage: float | None = 10,
) -> None:
    """Run Delany postprocessing with optional project and run-specific paths."""
    if not parcel_prediction_path.exists():
        raise ValueError(
            f"Parcel prediction path does not exist: {parcel_prediction_path}"
        )
    if not delany_prediction_path.exists():
        raise ValueError(
            f"Delany prediction path does not exist: {delany_prediction_path}"
        )

    if min_delany_area_percentage is not None and (
        not math.isfinite(min_delany_area_percentage)
        or not 0 <= min_delany_area_percentage <= 100
    ):
        raise ValueError(
            "min_delany_area_percentage must be a finite percentage between 0 and 100"
        )

    # Reproject the delany prediction to match the CRS of the parcel prediction.
    delany_prediction_reprojected_path = delany_prediction_path.with_stem(
        f"{delany_prediction_path.stem}_reproj"
    )
    parcel_crs = gfo.get_layerinfo(parcel_prediction_path).crs
    gfo.copy_layer(
        src=delany_prediction_path,
        dst=delany_prediction_reprojected_path,
        dst_crs=parcel_crs.to_string() if parcel_crs is not None else None,
        reproject=True,
        force=False,
    )

    # Add a column for the polygon area in the delany prediction.
    gfo.add_columns(
        path=delany_prediction_reprojected_path,
        new_columns=[("polygon_area", gfo.DataType.REAL, "ST_Area(geom)")],
        force_update=False,
    )

    # Compute the intersection between the parcel prediction and the delany prediction.
    intersection_path = delany_prediction_path.parent / "intersection.gpkg"
    gfo.intersection(
        input1_path=parcel_prediction_path,
        input2_path=delany_prediction_reprojected_path,
        output_path=intersection_path,
        input1_columns=[
            "classname_declared",
            "code_obj",
            "layer_id",
            "prc_id",
            "pred_consolidated",
        ],
        input1_columns_prefix="parcel_",
        input2_columns=["pred_consolidated", "polygon_area"],
        input2_columns_prefix="delany_",
        nb_parallel=8,
        force=False,
    )

    # Add a column for the intersection area in the intersection result.
    gfo.add_columns(
        path=intersection_path,
        new_columns=[("area", gfo.DataType.REAL, "ST_Area(geom)")],
        force_update=False,
    )

    # Filter the intersection result based on the minimum area percentage if specified.
    filtered_crop_intersection_path = intersection_path
    if min_delany_area_percentage is not None:
        filtered_crop_intersection_path = delany_prediction_path.parent / (
            f"intersection_min_overlap_{min_delany_area_percentage:g}pct.gpkg"
        )
        gfo.copy_layer(
            src=intersection_path,
            dst=filtered_crop_intersection_path,
            where=(
                f"area > delany_polygon_area * {min_delany_area_percentage / 100!s}"
            ),
            force=True,
        )

    # Dissolve the multi-crop intersection result to group by parcel identifiers.
    multi_crop_parcels_dissolved = (
        delany_prediction_path.parent / "multi_crop_parcels_dissolved.gpkg"
    )
    gfo.dissolve(
        input_path=filtered_crop_intersection_path,
        output_path=multi_crop_parcels_dissolved,
        groupby_columns=["parcel_code_obj", "parcel_layer_id", "parcel_prc_id"],
        agg_columns={
            "columns": [
                {
                    "column": "delany_pred_consolidated",
                    "agg": "concat",
                    "as": "delany_pred_consolidated_list",
                    "distinct": True,
                },
                {
                    "column": "delany_pred_consolidated",
                    "agg": "count",
                    "as": "delany_pred_consolidated_count",
                    "distinct": True,
                },
            ]
        },
        explodecollections=False,
        where_post="delany_pred_consolidated_count >= 2",
        nb_parallel=8,
        force=True,
    )

    # Join the dissolved multi-crop parcels with the original parcel prediction
    # to enrich the parcel data with delany predictions.
    multi_crop_parcels_filename = "multi_crop_parcels"
    if min_delany_area_percentage is not None:
        multi_crop_parcels_filename += f"_min_overlap_{min_delany_area_percentage:g}pct"
    multi_crop_parcels_path = (
        delany_prediction_path.parent / f"{multi_crop_parcels_filename}.gpkg"
    )
    gfo.join(
        input1_path=parcel_prediction_path,
        input2_path=multi_crop_parcels_dissolved,
        output_path=multi_crop_parcels_path,
        input1_on=["code_obj", "layer_id", "prc_id"],
        input2_on=["parcel_code_obj", "parcel_layer_id", "parcel_prc_id"],
        input1_columns_prefix="",
        input2_columns=[
            "delany_pred_consolidated_list",
            "delany_pred_consolidated_count",
        ],
        input2_columns_prefix="",
        nb_parallel=8,
        force=True,
    )
