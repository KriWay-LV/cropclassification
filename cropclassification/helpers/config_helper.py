"""Module that manages configuration data."""

import configparser
import json
import pprint
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any, Optional, Union

from cropclassification.util.mosaic_util import ImageProfile

config: configparser.ConfigParser
config_paths_used: list[Path]
config_overrules: list[str] = []
config_overrules_path: Optional[Path] = None
general: Any
calc_timeseries_params: Any
calc_marker_params: Any
calc_periodic_mosaic_params: Any
roi: Any
period: Any
images: Any
marker: Any
timeseries: Any
preprocess: Any
classifier: Any
postprocess: Any
columns: Any
paths: Any
image_profiles: dict[str, ImageProfile]


class ImageConfig:
    """Image configuration class."""

    def __init__(
        self,
        imageprofile_name: str,
        imageprofile: Optional[ImageProfile] = None,
        bands: Optional[list[str]] = None,
    ):
        """Constructor for ImageConfig.

        Args:
            imageprofile_name (str): the name of the image profile.
            imageprofile (Optional[ImageProfile], optional): ImageProfile to use for
                this Image. Defaults to None.
            bands (Optional[list[str]], optional): the bands to read. Defaults to None.
        """
        self.imageprofile_name = imageprofile_name
        if imageprofile is not None:
            self.imageprofile = imageprofile
        else:
            self.imageprofile = image_profiles[imageprofile_name]
        if bands is not None:
            self.bands = bands
        else:
            self.bands = self.imageprofile.bands  # type: ignore[assignment]


def read_config(
    config_paths: Union[list[Path], Path, None],
    default_basedir: Optional[Path] = None,
    overrules: list[str] = [],
    preload_defaults: bool = True,
):
    """Read cropclassification configuration file(s).

    Args:
        config_paths (Path): path(s) to the configuration file(s) to read. If None, and
            `preload_defaults=True`, only the defaults are loaded.
        default_basedir (Path, optional): if there relative paths are used in the
            configuration, this is the directory they will be resolved to.
            Defaults to None.
        overrules (List[str], optional): list of config options that will overrule other
            ways to supply configuration. They should be specified as a list of
            "<section>.<parameter>=<value>" strings. Defaults to [].
        preload_defaults (bool, optional): True to preload the config with the defaults
            in cropclassification.general.ini. Defaults to True.
    """
    # Check input parameters
    if default_basedir is not None and not default_basedir.exists():
        raise ValueError(f"default_basedir does not exist: {default_basedir}")
    # If only one config_path, make it a list to simplify code later on
    if config_paths is not None and not isinstance(config_paths, Iterable):
        config_paths = [config_paths]

    # Make sure general.ini is loaded first
    if preload_defaults:
        general_ini = Path(__file__).resolve().parent.parent / "general.ini"
        if config_paths is None:
            config_paths = [general_ini]
        else:
            config_paths = [general_ini, *config_paths]

    if config_paths is None:
        raise ValueError("config_paths is None and preload_defaults is False")

    # Check if all config paths exist + make sure all are Path objects
    for config_path in config_paths:
        if not config_path.exists():
            raise ValueError(f"Config file doesn't exist: {config_path}")

    # If there are overrules, write them to a temporary configuration file.
    global config_overrules
    config_overrules = overrules
    global config_overrules_path
    config_overrules_path = None
    if len(config_overrules) > 0:
        tmp_dir = Path(tempfile.gettempdir())
        tmp_dir.mkdir(parents=True, exist_ok=True)
        config_overrules_path = (
            Path(tempfile.mkdtemp(prefix="config_overrules_", dir=tmp_dir))
            / "config_overrules.ini"
        )

        # Create config parser, add all overrules
        overrules_parser = configparser.ConfigParser()
        for overrule in config_overrules:
            parts = overrule.split("=")
            if len(parts) != 2:
                raise ValueError(f"invalid config overrule found: {overrule}")
            key, value = parts
            parts2 = key.split(".")
            if len(parts2) != 2:
                raise ValueError(f"invalid config overrule found: {overrule}")
            section, parameter = parts2
            if section not in overrules_parser:
                overrules_parser[section] = {}
            overrules_parser[section][parameter] = value

        # Write to temp file and add file to config_paths
        with open(config_overrules_path, "w") as overrules_file:
            overrules_parser.write(overrules_file)
        config_paths.append(config_overrules_path)

    # Read and parse the config files
    global config
    config = configparser.ConfigParser(
        interpolation=configparser.ExtendedInterpolation(),
        converters={
            "list": lambda x: [i.strip() for i in x.split(",")],
            "listint": lambda x: [int(i.strip()) for i in x.split(",")],
            "listfloat": lambda x: [float(i.strip()) for i in x.split(",")],
            "dict": lambda x: None if x is None else json.loads(x),
            "path": lambda x: None if x is None else Path(x),
        },
        allow_no_value=True,
    )
    config.read(config_paths)

    # Basic check if the config file is of an old version.
    if "dirs" in config:
        raise ValueError(
            "Old version of config file detected. Please update your config file to "
            "the new format. More info in changelog of version 0.3.0."
        )

    # If the data_dir parameter is a relative path, try to resolve it towards
    # the default basedir of, if specfied.
    data_dir = config["paths"].getpath("data_dir")
    if not data_dir.is_absolute():
        if default_basedir is None:
            raise ValueError(
                "Config parameter paths.data_dir is relative, but no default_basedir "
                "supplied!"
            )
        data_dir_absolute = (default_basedir / data_dir).resolve()
        print(
            "Config parameter paths.data_dir was relative, so is now resolved to "
            f"{data_dir_absolute}"
        )
        config["paths"]["data_dir"] = data_dir_absolute.as_posix()

    # If the marker_basedir parameter is a relative path, try to resolve it towards
    # the default basedir of, if specfied.
    marker_basedir = config["paths"].getpath("marker_basedir")
    if not marker_basedir.is_absolute():
        if default_basedir is None:
            raise ValueError(
                "Config parameter paths.marker_basedir is relative, but no "
                "default_basedir supplied!"
            )
        marker_basedir_absolute = (default_basedir / marker_basedir).resolve()
        print(
            "Config parameter paths.marker_basedir was relative, so is now resolved to "
            f"{marker_basedir_absolute}"
        )
        config["paths"]["marker_basedir"] = marker_basedir_absolute.as_posix()

    # Fill out placeholder in the temp_dir (if it is there)
    tmp_dir_str = tempfile.gettempdir()
    config["paths"]["temp_dir"] = config["paths"]["temp_dir"].format(
        tmp_dir=tmp_dir_str
    )

    global config_paths_used
    config_paths_used = config_paths

    # Now set global variables to each section as shortcuts
    global general
    general = config["general"]
    global calc_timeseries_params
    calc_timeseries_params = config["calc_timeseries_params"]
    global calc_marker_params
    calc_marker_params = config["calc_marker_params"]
    global calc_periodic_mosaic_params
    if "calc_periodic_mosaic_params" in config:
        calc_periodic_mosaic_params = config["calc_periodic_mosaic_params"]
    else:
        calc_periodic_mosaic_params = None
    global roi
    roi = config["roi"]
    global period
    period = config["period"]
    global images
    images = config["images"]
    global marker
    marker = config["marker"]
    global timeseries
    timeseries = config["timeseries"]
    global preprocess
    preprocess = config["preprocess"]
    global classifier
    classifier = config["classifier"]
    global postprocess
    postprocess = config["postprocess"]
    global columns
    columns = config["columns"]
    global paths
    paths = config["paths"]

    # Check some parameters that should be overriden to have a valid config
    if config["roi"].get("roi_name") == "MUST_OVERRIDE":
        raise ValueError("roi.roi_name must be overridden")

    if config["paths"].get("images_periodic_dir") == "MUST_OVERRIDE":
        raise ValueError("paths.images_periodic_dir must be overridden")

    # Load image profiles
    global image_profiles
    image_profiles_config_filepath = paths.getpath("image_profiles_config_filepath")
    if image_profiles_config_filepath is not None:
        image_profiles = _get_image_profiles(
            paths.getpath("image_profiles_config_filepath")
        )
    else:
        # For backwards compatibility: old runs didn't have image profile configuration.
        image_profiles = {}


def parse_image_config(input) -> dict[str, ImageConfig]:
    """Parses the json input to a dictionary of ImageConfig objects."""
    result = None
    imageconfig_parsed = None
    try:
        imageconfig_parsed = json.loads(input)
    except Exception:
        pass

    if imageconfig_parsed is not None:
        # It was a json object, so parse as such
        result = {}
        for imageconfig in imageconfig_parsed:
            if isinstance(imageconfig, str):
                result[imageconfig] = ImageConfig(imageconfig)
            elif isinstance(imageconfig, dict):
                if len(imageconfig) != 1:
                    raise ValueError(
                        "Invalid element in json list images.images: this should be a "
                        f"single key dict, not: {imageconfig}"
                    )
                imageprofile_name = next(iter(imageconfig.keys()))
                bands = next(iter(imageconfig.values()))
                result[imageprofile_name] = ImageConfig(imageprofile_name, bands=bands)
            else:
                raise ValueError(
                    "Invalid element in json list images.images: only str or dict "
                    f"elements allowed, not: {imageconfig}"
                )
    else:
        # It was no json object, so it must be a list
        result = {i.strip(): ImageConfig(i.strip()) for i in input.split(",")}

    return result


def _get_image_profiles(image_profiles_path: Path) -> dict[str, ImageProfile]:
    # Cropclassification gives best results with time_reducer "mean" for both
    # sentinel 2 and sentinel 1 images.
    # Init
    if not image_profiles_path.exists():
        raise ValueError(f"Config file specified does not exist: {image_profiles_path}")

    # Read config file...
    profiles_config = configparser.ConfigParser(
        interpolation=configparser.ExtendedInterpolation(),
        converters={
            "list": lambda x: [i.strip() for i in x.split(",")],
            "dict": lambda x: None if x == "None" else json.loads(x),
        },
        allow_no_value=True,
    )
    profiles_config.read(image_profiles_path)

    # Prepare data
    profiles = {}
    for profile in profiles_config.sections():
        profiles[profile] = ImageProfile(
            name=profile,
            satellite=profiles_config[profile]["satellite"],
            image_source=profiles_config[profile]["image_source"],
            bands=profiles_config[profile].getlist("bands"),
            collection=profiles_config[profile].get("collection"),
            time_reducer=profiles_config[profile].get("time_reducer"),
            period_name=profiles_config[profile].get("period_name"),
            period_days=profiles_config[profile].getint("period_days"),
            base_image_profile=profiles_config[profile].get("base_image_profile"),
            index_type=profiles_config[profile].get("index_type"),
            pixel_type=profiles_config[profile].get("pixel_type"),
            max_cloud_cover=profiles_config[profile].getfloat("max_cloud_cover"),
            process_options=profiles_config[profile].getdict("process_options"),
            job_options=profiles_config[profile].getdict("job_options"),
        )

    # Do some extra validations on the profiles read.
    _validate_image_profiles(profiles)

    return profiles


def _validate_image_profiles(profiles: dict[str, ImageProfile]):
    # Check that all base_image_profile s are actually existing image profiles.
    for profile in list(profiles):
        base_image_profile = profiles[profile].base_imageprofile
        if base_image_profile is not None and base_image_profile not in profiles:
            raise ValueError(
                f"{base_image_profile=} not found for profile {profiles[profile]}"
            )


def pformat_config():
    """Formats the config as a pretty string."""
    message = (
        f"Config files used: {pprint.pformat(config_paths_used)} \n"
        "Config info listing:\n"
        f"{pprint.pformat(as_dict())}"
    )

    return message


def as_dict():
    """Converts the config objects into a dictionary.

    The resulting dictionary has sections as keys which point to a dict of the
    sections options as key => value pairs.
    """
    the_dict = {}
    for section in config.sections():
        the_dict[section] = {}
        for key, val in config.items(section):
            the_dict[section][key] = val
    the_dict["image_profiles"] = {}
    for image_profile in image_profiles:
        the_dict["image_profiles"][image_profile] = image_profiles[
            image_profile
        ].__dict__

    return the_dict
