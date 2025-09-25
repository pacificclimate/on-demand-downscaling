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


def _point_in_mask(nc_url, varname, point, latvar="lat", lonvar="lon", time_index=0):
    """
    Check if (lat, lon) is within [lat, lon] bounds of nc_url and not masked/missing
    at the nearest grid cell for `varname`.
    """
    with Dataset(nc_url) as ds:
        lat = ds.variables[latvar][:]
        lon = ds.variables[lonvar][:]
        plat, plon = float(point[0]), float(point[1])

        if plat < lat[0] or plat > lat[-1] or plon < lon[0] or plon > lon[-1]:
            return False

        lat_index = int(np.argmin(np.abs(lat - plat)))
        lon_index = int(np.argmin(np.abs(lon - plon)))

        var = ds.variables[varname]
        cell = (
            var[time_index, lat_index, lon_index]
            if getattr(var, "ndim", 2) == 3
            else var[lat_index, lon_index]
        )

        # masked array?
        if np.ma.isMaskedArray(cell) and np.ma.getmask(cell):
            return False

        # plain scalar: NaN or fill/missing?
        try:
            val = float(cell)
        except Exception:
            return True

        if np.isnan(val):
            return False

        for attr in ("_FillValue", "missing_value"):
            if hasattr(var, attr):
                mv = getattr(var, attr)
                mv_list = (
                    list(mv)
                    if np.iterable(mv) and not isinstance(mv, (str, bytes))
                    else [mv]
                )
                for mvv in mv_list:
                    try:
                        if mvv is not None and float(val) == float(mvv):
                            return False
                    except Exception:
                        pass
        return True


def in_bc(point):
    url = f"{THREDDS_BASE}/storage/data/climate/PRISM/dataportal/pr_monClim_PRISM_historical_run1_198101-201012.nc"
    return _point_in_mask(url, "pr", point)


def in_canada(point):
    url = f"{THREDDS_BASE}/storage/data/climate/observations/gridded/Canada_mosaic_30arcsec/pr_monClim_Canada_mosaic_30arcsec_198101-201012.nc"
    return _point_in_mask(url, "pr", point)


def resolve_gcm_mask_url(state, gcm_var):
    """
    Return (url, var) for gcm_var.
    Assumes UI guarantees: if dataset == CMIP6, then scenario is selected.
    """
    internal_ds = getattr(state, "internal_dataset", None)  # "PNWNAmet" | "CMIP6"
    internal_tech = getattr(state, "internal_technique", None)  # "BCCAQv2" | "MBCn"
    model = (getattr(state, "model", "") or "").strip()
    scenario = (getattr(state, "scenario", "") or "").strip()

    # PCIC-Blend (PNWNAmet):
    if internal_ds == "PNWNAmet":
        url = f"{THREDDS_BASE}/storage/data/projects/dataportal/data/vic-gen2-forcing/PNWNAmet_{gcm_var}_invert_lat.nc"
        return url, gcm_var
    # CMIP6:
    tech_dir = "BCCAQ2" if internal_tech == "BCCAQv2" else "MBCn"
    model_dir = model if internal_tech == "BCCAQv2" else f"{model}_10"
    catalog = f"{THREDDS_CATALOG}/storage/data/climate/downscale/{tech_dir}/CMIP6_{internal_tech}/{model_dir}/catalog.html"
    session = HTMLSession()
    r = session.get(catalog)
    for name in (tt.text for tt in r.html.find("tt")):
        if (gcm_var in name) and (scenario in name):
            url = f"{THREDDS_BASE}/storage/data/climate/downscale/{tech_dir}/CMIP6_{internal_tech}/{model_dir}/{name}"
            return url, gcm_var

    raise LookupError(
        f"No CMIP6 file for var={gcm_var}, scenario={scenario}, model={model}, tech={internal_tech}."
    )


def in_gcm_for_vars(point, state, selected_vars):
    """
    Check GCM mask for multiple variables.
    selected_vars: list like ["pr","tasmax", ...]
    """
    # For each var, map to a representative GCM var and test
    for clim_var in dict.fromkeys(selected_vars):
        gcm_var = "tasmax" if clim_var == "tasmean" else clim_var
        url, var = resolve_gcm_mask_url(state, gcm_var)
        if not _point_in_mask(url, var, point):
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
