import numpy as np
from netCDF4 import Dataset, date2num
from datetime import date
from datetime import datetime
from time import sleep
from requests_html import HTMLSession
from ipywidgets import *
from ipyleaflet import *
from IPython import display as ipydisplay
from .config import *


def in_bc(point):
    """Check if a given point is within
    the BC PRISM grid."""
    bc = f"{THREDDS_BASE}/storage/data/climate/PRISM/dataportal/pr_monClim_PRISM_historical_run1_198101-201012.nc"
    bc_data = Dataset(bc)
    bc_lat = bc_data.variables["lat"][:]
    bc_lon = bc_data.variables["lon"][:]
    # Check if center point is within lat/lon grid
    if (
        (point[0] < bc_lat[0])
        or (point[0] > bc_lat[-1])
        or (point[1] < bc_lon[0])
        or (point[1] > bc_lon[-1])
    ):
        return False
    # Check if center point is closest to a masked data value
    else:
        lat_index = np.argmin(np.abs(bc_lat - point[0]))
        lon_index = np.argmin(np.abs(bc_lon - point[1]))
        pr = bc_data.variables["pr"][0, lat_index, lon_index]
        if pr.mask:
            return False
    return True


def in_canada(point):
    """Check if a given point is within
    the Canada mosaic grid."""
    ca = f"{THREDDS_BASE}/storage/data/climate/observations/gridded/Canada_mosaic_30arcsec/tmin_monClim_Canada_mosaic_30arcsec_198101-201012.nc"
    ca_data = Dataset(ca)
    ca_lat = ca_data.variables["lat"][:]
    ca_lon = ca_data.variables["lon"][:]
    # Check if center point is within lat/lon grid
    if (
        (point[0] < ca_lat[0])
        or (point[0] > ca_lat[-1])
        or (point[1] < ca_lon[0])
        or (point[1] > ca_lon[-1])
    ):
        return False
    # Check if center point is closest to a masked data value
    else:
        lat_index = np.argmin(np.abs(ca_lat - point[0]))
        lon_index = np.argmin(np.abs(ca_lon - point[1]))
        tmin = ca_data.variables["tmin"][0, lat_index, lon_index]
        if tmin.mask:
            return False
    return True


def get_subdomain(lat_min, lat_max, lon_min, lon_max, color, name):
    """Create a rectangle with the vertices at the lat/lon coordinates
    of the chosen subdomain. Blue is the GCM, and red is the PRISM observations."""
    bounds = [(lat_min, lon_min), (lat_max, lon_max)]
    return Rectangle(
        bounds=bounds,
        color=color,
        fill_color=color,
        fill_opacity=0.3,
        stroke=True,
        draggable=False,
        name=name,
    )


def get_models():
    """Get the list of available CMIP6 models."""
    session = HTMLSession()
    r = session.get(
        f"{THREDDS_CATALOG}/storage/data/climate/downscale/BCCAQ2/CMIP6_BCCAQv2/catalog.html"
    )
    exclude = [
        "AgroClimate/",
        "CMIP6_BCCAQv2",
        "CWEC2020_Factors/",
        "Degree_Climatologies/",
        "Ensemble_Averages/",
        "nobackup/",
        "--",
        "",
    ]
    models = [tt.text[:-1] for tt in r.html.find("tt") if tt.text not in exclude]
    models.sort()
    return models


def get_time_range(dataset, downscaled_period):
    """Get the indices of the start and end of the
    selected downscaled period."""
    calendar = dataset.variables["time"].calendar
    units = dataset.variables["time"].units
    start, end = downscaled_period.split("-")
    start += "-01-01"
    end_date = "-12-30" if calendar == "360_day" else "-12-31"
    end += end_date

    date_format = "%Y-%m-%d"
    start_bound = date2num(
        datetime.strptime(start, date_format), units=units, calendar=calendar
    )
    end_bound = date2num(
        datetime.strptime(end, date_format), units=units, calendar=calendar
    )
    return f"[{start_bound}:{end_bound}]"


def get_index_range(arr, min_val, max_val):
    """Compute the indices in an array that correspond to the array's values
    closest to desired min/max values."""
    min_index = np.argmin(np.abs(arr - min_val))
    max_index = np.argmin(np.abs(arr - max_val))
    return (min_index, max_index)


def find_opendap_url(variable, outputs):
    for ds in outputs:
        if ds.get("clim_var") == variable:
            return ds.get("opendap_url")
    return None


def get_output(resp):
    """Get the URL of the downscaling/climate index output file for downloading."""
    if resp.isNotComplete():
        print("Process is not complete.")
    else:
        print(f"Process status: {resp.status}")
        print(f"Link to process output: {resp.get()[0].replace('dodsC', 'fileServer')}")


def setup_index_process_params(identifier, resolution=None, threshold=None):
    params = {}
    config = INDEX_PROCESS_CONFIG.get(identifier, INDEX_PROCESS_CONFIG["*"])

    # --- Time Resolution (unchanged) ---
    output_suffix = "annual"
    if resolution == "Monthly":
        params["freq"] = "MS"
        output_suffix = "monthly"
    elif resolution == "Seasonal":
        params["freq"] = "QS-DEC"
        output_suffix = "seasonal"
    elif resolution:
        params["freq"] = "YS"
        if resolution in MONTHS:
            params["month"] = MONTHS.index(resolution) + 1
            output_suffix = resolution[:3].lower()
        elif resolution in SEASONS:
            params["season"] = resolution.split("-")[1]
            output_suffix = params["season"].lower()

    # --- Threshold Param ---
    param_key = config.get("param_key", "thresh")
    num_for_prefix = None
    if "param_overrides" in config:
        params.update(config["param_overrides"])
        num_for_prefix = None
    elif threshold is not None:
        if "threshold_parser" in config:
            parsed = config["threshold_parser"](threshold)
        else:
            parsed = threshold
        params[param_key] = parsed

        if "number_parser" in config:
            num_for_prefix = config["number_parser"](threshold)
        else:
            num_for_prefix = (
                parsed if isinstance(parsed, (str, int, float)) else threshold
            )

    # --- Output Name ---
    if config.get("output_prefix"):
        try:
            prefix = config["output_prefix"].format(
                **{param_key: params[param_key]}, num=num_for_prefix
            )
        except Exception:
            prefix = identifier.replace("_", "")
    else:
        prefix = identifier.replace("_", "")
    params["output_name"] = f"{prefix}_{output_suffix}"

    return params


def get_output_thredds_location(url):
    """Determine the location of the downscaled output on
    THREDDS so that it can be properly passed to finch."""
    print(f"output url: {url}")
    if "wpsoutputs" in url:
        return THREDDS_BASE + "/ODDS_outputs" + url.split("wpsoutputs")[1]
    else:  # THREDDS location, Replace with OPeNDAP
        return url.replace("fileServer", "dodsC")


def get_output_thredds_fileserver_location(url):
    """Determine the location of the downscaled output on
    THREDDS so that it can be shared with the user."""
    print(f"output url: {url}")
    if "wpsoutputs" in url:
        return (
            THREDDS_BASE.replace("dodsC", "fileServer")
            + "/ODDS_outputs"
            + url.split("wpsoutputs")[1]
        )
    else:
        return url.replace("dodsC", "fileServer")
