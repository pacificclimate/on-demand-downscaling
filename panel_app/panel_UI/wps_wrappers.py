from .config import (
    finch,
    chickadee,
    CLIM_VARS,
    THREDDS_BASE,
    THREDDS_CATALOG,
    DEFAULT_START_DATE,
    DEFAULT_END_DATE,
)
from .panel_helpers import (
    get_index_range,
    get_time_range,
    get_output_thredds_location,
    get_output_thredds_fileserver_location,
    find_opendap_url,
    setup_index_process_params,
)

from requests_html import HTMLSession
from netCDF4 import Dataset


def run_single_downscaling(ds_params):
    clim_var = ds_params["clim_var"]
    model = ds_params["model"]
    technique = ds_params["technique"]
    canesm5_run = ds_params.get("canesm5_run")
    scenario = ds_params["scenario"]
    period = ds_params["period"]
    region = ds_params["region"]
    center_point = ds_params.get("center_point")
    bounds = ds_params.get("bounds", {})
    dataset = ds_params["dataset"]
    dataset_name = dataset.split(" ")[0]

    # Unpack bounds
    lat_min_obs = bounds.get("lat_min_obs")
    lat_max_obs = bounds.get("lat_max_obs")
    lon_min_obs = bounds.get("lon_min_obs")
    lon_max_obs = bounds.get("lon_max_obs")
    lat_min_gcm = bounds.get("lat_min_gcm")
    lat_max_gcm = bounds.get("lat_max_gcm")
    lon_min_gcm = bounds.get("lon_min_gcm")
    lon_max_gcm = bounds.get("lon_max_gcm")

    if clim_var == "tasmean":
        gcm_var = "tasmax"
    else:
        gcm_var = clim_var
    obs_var = CLIM_VARS[clim_var]

    if dataset_name == "PNWNAmet":
        gcm_file = f"{THREDDS_BASE}/storage/data/projects/dataportal/data/vic-gen2-forcing/PNWNAmet_{gcm_var}_invert_lat.nc"
    else:
        if technique == "BCCAQv2":
            technique_dir = "BCCAQ2"
            model_dir = model
        else:
            technique_dir = "MBCn"
            model_dir = model + "_10"
        model_catalog = f"{THREDDS_CATALOG}/storage/data/climate/downscale/{technique_dir}/CMIP6_{technique}/{model_dir}/catalog.html"

        session = HTMLSession()
        r = session.get(model_catalog)
        file = ""
        # Locate the filename in THREDDS based on the parameter values
        for tt in r.html.find("tt"):
            file = tt.text
            if (gcm_var in file) and (scenario in file):
                if (model == "CanESM5") and (canesm5_run not in file):
                    continue
                break
        gcm_file = f"{THREDDS_BASE}/storage/data/climate/downscale/{technique_dir}/CMIP6_{technique}/{model_dir}/{file}"

    obs_file = f"{THREDDS_BASE}/storage/data/climate/PRISM/dataportal/{obs_var}_monClim_PRISM_historical_run1_198101-201012.nc"
    print(f"Using GCM file: {gcm_file}")
    print(f"Using Obs file: {obs_file}")
    gcm_dataset = Dataset(gcm_file)
    obs_dataset = Dataset(obs_file)
    print(f"{gcm_dataset.variables.keys()}")
    print(f"{obs_dataset.variables.keys()}")
    # Obtain the datasets' latitudes and longitudes to determine the subdomains
    try:
        print(f"Reading GCM: lat, lon")
        gcm_lats = gcm_dataset.variables["lat"][:]
        gcm_lons = gcm_dataset.variables["lon"][:]
        obs_lats = obs_dataset.variables["lat"][:]
        obs_lons = obs_dataset.variables["lon"][:]
        print("✅ Successfully read lat/lon arrays.")
    except Exception as e:
        print(f"❗ ERROR reading lat/lon: {e}")
        raise
    print(f"Fetching index range:")
    # Use the stored subdomain bounds from the map interaction
    gcm_lat_indices = get_index_range(gcm_lats, lat_min_gcm, lat_max_gcm)
    gcm_lon_indices = get_index_range(gcm_lons, lon_min_gcm, lon_max_gcm)
    obs_lat_indices = get_index_range(obs_lats, lat_min_obs, lat_max_obs)
    obs_lon_indices = get_index_range(obs_lons, lon_min_obs, lon_max_obs)
    try:
        print(f"Reading GCM: lat, lon indices")
        gcm_lat_indices = get_index_range(gcm_lats, lat_min_gcm, lat_max_gcm)
        gcm_lon_indices = get_index_range(gcm_lons, lon_min_gcm, lon_max_gcm)
        obs_lat_indices = get_index_range(obs_lats, lat_min_obs, lat_max_obs)
        obs_lon_indices = get_index_range(obs_lons, lon_min_obs, lon_max_obs)
        print("✅ Successfully read lat/lon indices.")
    except Exception as e:
        print(f"❗ ERROR reading lat/lon indices: {e}")
        raise
    gcm_lat_range = f"[{gcm_lat_indices[0]}:{gcm_lat_indices[1]}]"
    gcm_lon_range = f"[{gcm_lon_indices[0]}:{gcm_lon_indices[1]}]"
    obs_lat_range = f"[{obs_lat_indices[0]}:{obs_lat_indices[1]}]"
    obs_lon_range = f"[{obs_lon_indices[0]}:{obs_lon_indices[1]}]"

    # Use full time range of PNWNAmet datasets, but user-specified range for CMIP6
    print("Setting time ranges")
    if dataset_name == "PNWNAmet":
        gcm_ntime = len(gcm_dataset.variables["time"][:])
        gcm_time_range = f"[0:{gcm_ntime - 1}]"
    else:
        gcm_time_range = get_time_range(gcm_dataset, period)
    obs_ntime = len(obs_dataset.variables["time"][:])
    obs_time_range = f"[0:{obs_ntime - 1}]"

    # Request a subset of each dataset based on the array indices for each subdomain
    gcm_subset_file = f"{gcm_file}?time{gcm_time_range},lat{gcm_lat_range},lon{gcm_lon_range},{gcm_var}{gcm_time_range}{gcm_lat_range}{gcm_lon_range}"
    obs_subset_file = f"{obs_file}?time{obs_time_range},lat{obs_lat_range},lon{obs_lon_range},climatology_bounds,crs,{obs_var}{obs_time_range}{obs_lat_range}{obs_lon_range}"

    # If tasmean is requested, compute it via finch using the tasmax and tasmin subsets
    if clim_var == "tasmean":
        gcm_var = "tasmean"
        tasmax_file = gcm_subset_file
        tasmin_file = tasmax_file.replace("tasmax", "tasmin")
        print("Starting tasmean process")
        tasmean = finch.tg(
            tasmax=tasmax_file, tasmin=tasmin_file, output_name="tasmean"
        )
        while tasmean.isNotComplete():
            sleep(3)
        gcm_file = (
            THREDDS_BASE + "/ODDS_outputs" + tasmean.get()[0].split("wpsoutputs")[1]
        )
        gcm_subset_file = gcm_file

    gcm_dataset.close()
    obs_dataset.close()

    # Put together the parameters for chickadee.ci
    region_name = region.lower().replace(" ", "-")
    gcm_varname = "tg" if gcm_var == "tasmean" else gcm_var
    chickadee_params = {
        "gcm_file": gcm_subset_file,
        "obs_file": obs_subset_file,
        "gcm_varname": gcm_varname,
        "obs_varname": obs_var,
        "max_gb": 0.5,
        "start_date": DEFAULT_START_DATE,
        "end_date": DEFAULT_END_DATE,
    }

    if gcm_var in ["pr", "tg"]:
        chickadee_params["units_bool"] = False
        if gcm_var == "pr":
            chickadee_params["pr_units"] = "mm/day"

    if dataset_name == "PNWNAmet":
        chickadee_params["out_file"] = (
            f"{gcm_var}_{dataset_name}_1945-2012_{region_name}.nc"
        )
    else:
        if canesm5_run and model == "CanESM5":
            chickadee_params["out_file"] = (
                f"{gcm_var}_{dataset_name}_{technique}_{model}_{canesm5_run}_{scenario}_{period}_{region_name}.nc"
            )
        else:
            chickadee_params["out_file"] = (
                f"{gcm_var}_{dataset_name}_{technique}_{model}_{scenario}_{period}_{region_name}.nc"
            )

    try:
        print(f"Starting downscaling process for variable {clim_var} ")
        ci_process = chickadee.ci(**chickadee_params)
        print(f"Status URL: {ci_process.statusLocation}")
        print("ci proc:", ci_process)
        final_output = ci_process.get()[0]

        print(f"Final output (HTTP download): {final_output}")

    except Exception as e:
        error_message = str(e)
        if (
            "ServerBusy" in error_message
            and "Maximum number of processes in queue reached" in error_message
        ):
            print("⚠️ SERVER BUSY")
            print(
                "The processing queue is currently full. Your job cannot be submitted at this time."
            )
            print("Please wait for jobs to complete and try again")
        else:
            print(f"⚠️ ERROR: An unexpected error occurred during downscaling:")
            print(f"{str(e)}")
            print("Please check your inputs and try again.")
    print("ci proc:", ci_process)

    return {
        "clim_var": clim_var,
        "fileserver_url": get_output_thredds_fileserver_location(final_output),
        "status_url": ci_process.statusLocation,
        "opendap_url": get_output_thredds_location(final_output),
    }


def run_single_index(ix_params, downscaling_outputs):
    func_name = ix_params["func_name"]
    variable = ix_params["variable"]
    resolution = ix_params.get("resolution")
    threshold = ix_params.get("threshold")
    index_name = ix_params["index_name"]

    try:
        process = getattr(finch, func_name)
        opendap_urls = []
        if variable == "multivar":
            # For multivariate indices, we need both tasmax and tasmin URLs
            tasmax_url = find_opendap_url("tasmax", downscaling_outputs)
            tasmin_url = find_opendap_url("tasmin", downscaling_outputs)
            opendap_urls = [tasmin_url, tasmax_url]
        else:
            opendap_urls = [find_opendap_url(variable, downscaling_outputs)]

        if not opendap_urls:
            return f"{index_name}: ❌ No input file"

        params = setup_index_process_params(func_name, resolution, threshold)
        print("Calling finch.dtr with URLs (tasmin, tasmax):", opendap_urls)
        process_result = process(*opendap_urls, **params)
        output_url = process_result.get()[0]

        return f"{index_name}: {get_output_thredds_fileserver_location(output_url)}"

    except Exception as e:
        return f"{index_name}: ❌ Error {str(e)}"
