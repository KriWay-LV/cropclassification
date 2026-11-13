"""Run Delany prediction postprocessing and identify multi-crop parcels."""

import logging
from pathlib import Path

import geofileops as gfo

# Get a logger...
logger = logging.getLogger(__name__)


def run(
    parcel_prediction_path: Path,
    delany_prediction_path: Path,
    negative_buffer_distance: float = 5,
    minimum_parcel_area: float = 10,
) -> None:
    """Run Delany postprocessing and retain intersections above the area threshold."""
    if not parcel_prediction_path.exists():
        raise ValueError(
            f"Parcel prediction path does not exist: {parcel_prediction_path}"
        )
    if not delany_prediction_path.exists():
        raise ValueError(
            f"Delany prediction path does not exist: {delany_prediction_path}"
        )
    if minimum_parcel_area < 0:
        raise ValueError("minimum_parcel_area must be non-negative")

    # Add negative buffer to the delany prediction.
    delany_prediction_buffered_path = delany_prediction_path.with_stem(
        f"{delany_prediction_path.stem}_buf{negative_buffer_distance:g}m"
    )
    gfo.buffer(
        input_path=delany_prediction_path,
        output_path=delany_prediction_buffered_path,
        distance=-negative_buffer_distance,
        force=True,
    )

    # Add a column for the polygon area in the delany prediction.
    gfo.add_columns(
        path=delany_prediction_buffered_path,
        new_columns=[("area", gfo.DataType.REAL, "ST_Area(geom)")],
        force_update=True,
    )

    # Compute the intersection between the parcel prediction and the delany prediction.
    intersection_path = delany_prediction_path.parent / "intersection.gpkg"
    intersection_filtered_path = (
        delany_prediction_path.parent
        / f"intersection_filtered_{minimum_parcel_area:g}a.gpkg"
    )
    gfo.intersection(
        input1_path=parcel_prediction_path,
        input2_path=delany_prediction_buffered_path,
        output_path=intersection_path,
        input1_columns=[
            "classname_declared",
            "code_obj",
            "layer_id",
            "prc_id",
            "pred_consolidated",
        ],
        input1_columns_prefix="parcel_",
        input2_columns=["pred_consolidated", "area"],
        input2_columns_prefix="delany_",
        nb_parallel=8,
        force=True,
    )

    # Add a column for the intersection area in the intersection result.
    gfo.add_columns(
        path=intersection_path,
        new_columns=[("area", gfo.DataType.REAL, "ST_Area(geom)")],
        force_update=True,
    )

    gfo.select(
        input_path=intersection_path,
        output_path=intersection_filtered_path,
        sql_stmt=f"""
            SELECT {{geometrycolumn}}
                   {{columns_to_select_str}}
              FROM "{{input_layer}}" layer
             WHERE ST_Area({{geometrycolumn}})
                   > {minimum_parcel_area * 100}
            {{batch_filter}}
        """,
        nb_parallel=8,
        force=True,
    )

    # Dissolve the multi-crop intersection result to group by parcel identifiers.
    multi_crop_parcels_dissolved = (
        delany_prediction_path.parent / "multi_crop_parcels_dissolved.gpkg"
    )
    gfo.dissolve(
        input_path=intersection_filtered_path,
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
    multi_crop_parcels_path = delany_prediction_path.parent / "multi_crop_parcels.gpkg"
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
