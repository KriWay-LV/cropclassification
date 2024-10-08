"""
Calaculate the timeseries data per week based on per image data.
"""

import os
from datetime import datetime
from pathlib import Path

import cropclassification.preprocess._timeseries_helper as ts_helper
from cropclassification.helpers import config_helper as conf
from cropclassification.helpers import log_helper


def main():
    config_paths = [Path("config/general.ini"), Path("config/local_overrule.ini")]
    year = 2018

    # Read the configuration files
    conf.read_config(config_paths)

    # Init logging
    base_log_dir = conf.paths.getpath("log_dir")
    log_dir = (
        base_log_dir / f"{os.sep}calc_dias_weekly{datetime.now():%Y-%m-%d_%H-%M-%S}"
    )
    log_level = conf.general.get("log_level")
    global logger
    logger = log_helper.main_log_init(log_dir, __name__, log_level)
    logger.info(f"Config used: \n{conf.pformat_config()}")

    # Get the config needed
    timeseries_per_image_dir = conf.paths.getpath("timeseries_per_image_dir")
    timeseries_periodic_dir = conf.paths.getpath("timeseries_periodic_dir")

    # Input features file depends on the year
    if year == 2017:
        input_features_filename = "Prc_BEFL_2017_2019-06-14_bufm5.shp"
    elif year == 2018:
        input_features_filename = "Prc_BEFL_2018_2019-06-14_bufm5.shp"
    elif year == 2019:
        # input_features_filename = "Prc_BEFL_2019_2019-06-25_bufm5.shp"
        input_features_filename = "Prc_BEFL_2019_2019-07-02_bufm5.shp"
    else:
        raise Exception(f"Not a valid year: {year}")

    # Calculate!
    input_parcel_path = conf.paths.getpath("input_dir") / input_features_filename
    ts_helper.calculate_periodic_timeseries(
        parcel_path=input_parcel_path,
        timeseries_per_image_dir=timeseries_per_image_dir,
        start_date=datetime.fromisoformat(f"{year}-03-15"),
        end_date=datetime.fromisoformat(f"{year}-08-15"),
        sensordata_to_get=["SENSORDATA_S1_COHERENCE"],
        timeseries_periodic_dir=timeseries_periodic_dir,
        force=False,
    )


if __name__ == "__main__":
    main()
