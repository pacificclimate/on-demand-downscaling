import os
import shapely.geometry
import numpy as np
from birdy import WPSClient
from netCDF4 import Dataset, date2num
from inspect import getfullargspec
from datetime import date
from datetime import datetime
from time import sleep
from requests_html import HTMLSession
from ipywidgets import *
from ipyleaflet import *
from IPython import display as ipydisplay
from xarray import open_mfdataset
from tempfile import NamedTemporaryFile
from functools import partial

# Instantiate the clients to the two birds. This instantiation also takes advantage of asynchronous execution by setting `progress` to True.
host = os.getenv("BIRDHOUSE_HOST_URL", "marble-dev01.pcic.uvic.ca")
chickadee_url = f"http://{host}:30102"
#chickadee_url = "http://localhost:5000/wps"
chickadee = WPSClient(chickadee_url, progress=True)
finch_url = f"https://{host}/twitcher/ows/proxy/finch/wps"
finch = WPSClient(finch_url, progress=True)

# These outputs store the WPS responses to track the bird processes
downscaled_outputs = {"pr": [], "tasmax": [], "tasmin": [], "tasmean": []}
index_outputs = []

sub_layers = LayerGroup()
thredds_base = (
    f"https://{host}/twitcher/ows/proxy/thredds/dodsC/datasets"
)
thredds_catalog = (
    f"https://{host}/twitcher/ows/proxy/thredds/catalog/datasets"
)


##################### Functions for using chickadee to downscale GCM data #####################################

output_widget_downscaling = Output()  # Used to print bird progress to main workflow

def in_bc(point):
    bc = f"{thredds_base}/storage/data/climate/PRISM/dataportal/pr_monClim_PRISM_historical_run1_198101-201012.nc"
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


def get_subdomain(lat_min, lat_max, lon_min, lon_max, color, name):
    coords = [(lat_min, lon_min), (lat_max, lon_max)]
    return Rectangle(bounds=coords, color=color, name=name, draggable=True)


def get_models():
    session = HTMLSession()
    r = session.get(
        f"{thredds_catalog}/storage/data/climate/downscale/BCCAQ2/CMIP6_BCCAQv2/catalog.html"
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


def handle_dataset_change(change):
    technique.disabled = not technique.disabled
    model.disabled = not model.disabled
    scenario.disabled = not scenario.disabled
    period.disabled = not period.disabled

def handle_model_change(change):
    if model.value == "CanESM5":
        canesm5_run.disabled = False
    else:
        canesm5_run.disabled = True

@output_widget_downscaling.capture()
def handle_interact(**kwargs):
    point = (
        round(kwargs.get("coordinates")[0], 5),
        round(kwargs.get("coordinates")[1], 5),
    )
    center_hover.value = str(point)
    if kwargs.get("type") == "click":
        # Check if point is within PRISM region
        if not in_bc(point):
            print("Please select a point within BC\n")
            return
        # Remove previous center point and subdomains
        region.value = ""
        if sub_layers in m.layers:
            m.remove_layer(sub_layers)
        for layer in sub_layers.layers:
            sub_layers.remove_layer(layer)
        
        # Add new subdomains
        m.center_point = point
        center.value = str(m.center_point)
        center_marker = Marker(location=m.center_point, name="Marker")

        m.lat_min_obs, m.lat_max_obs = (
            m.center_point[0] - 1.25,
            m.center_point[0] + 1.25,
        )
        m.lon_min_obs, m.lon_max_obs = (
            m.center_point[1] - 1.25,
            m.center_point[1] + 1.25,
        )
        m.lat_min_gcm, m.lat_max_gcm = (
            m.center_point[0] - 1.5,
            m.center_point[0] + 1.5,
        )
        m.lon_min_gcm, m.lon_max_gcm = (
            m.center_point[1] - 1.5,
            m.center_point[1] + 1.5,
        )

        gcm_subdomain = get_subdomain(
            m.lat_min_gcm, m.lat_max_gcm, m.lon_min_gcm, m.lon_max_gcm, "blue", "GCM"
        )
        obs_subdomain = get_subdomain(
            m.lat_min_obs, m.lat_max_obs, m.lon_min_obs, m.lon_max_obs, "red", "Obs"
        )

        sub_layers.add_layer(center_marker)
        sub_layers.add_layer(gcm_subdomain)
        sub_layers.add_layer(obs_subdomain)
        m.add_layer(sub_layers)

def get_time_range(dataset, downscaled_period):
    calendar = dataset.variables["time"].calendar
    units = dataset.variables["time"].units
    start, end = downscaled_period.split("-")
    start += "-01-01"
    end_date = "-12-30" if calendar == "360_day" else "-12-31"
    end += end_date

    date_format = "%Y-%m-%d"
    start_bound = date2num(datetime.strptime(start, date_format), units=units, calendar=calendar)    
    end_bound = date2num(datetime.strptime(end, date_format), units=units, calendar=calendar)
    return f"[{start_bound}:{end_bound}]"

def concat_baseline_future(gcm_dataset, gcm_subset_file, gcm_time_range):
    baseline_time_range = get_time_range(gcm_dataset, "1981-2010")
    baseline_subset_file = gcm_subset_file.replace(gcm_time_range, baseline_time_range)
    tf = NamedTemporaryFile(suffix=".nc", delete=False)
    with open_mfdataset([baseline_subset_file, gcm_subset_file], combine="nested", concat_dim="time") as concat_dset:
        concat_dset.to_netcdf(tf.name)
    gcm_subset_file = tf.name
    return gcm_subset_file    

@output_widget_downscaling.capture()
def handle_run_downscaling(arg):
    if not m.center_point:
        print("Please select a center point for the downscaling subdomain before running\n")
        return
    if region.value == "":
        print("Please enter a region name for the downscaling subdomain before running\n")
        return
    # Obtain the input data files from the THREDDS data server (eg. https://marble-dev01.pcic.uvic.ca/twitcher/ows/proxy/thredds/catalog.html)
    data_vars = {"pr": "pr", "tasmax": "tmax", "tasmin": "tmin", "tasmean": "tas"}

    if clim_vars.value == "tasmean":
        gcm_var = "tasmax"
    else:
        gcm_var = clim_vars.value
    obs_var = data_vars[clim_vars.value]

    dataset_name = dataset.value.split(" ")[0]
    if dataset_name == "PNWNAmet":
        gcm_file = f"{thredds_base}/storage/data/projects/dataportal/data/vic-gen2-forcing/PNWNAmet_{gcm_var}_invert_lat.nc"
    else:
        if technique.value == "BCCAQv2":
            technique_dir = "BCCAQ2"
            model_dir = model.value
        else:
            technique_dir = "MBCn"
            model_dir = model.value + "_10"
        model_catalog = f"{thredds_catalog}/storage/data/climate/downscale/{technique_dir}/CMIP6_{technique.value}/{model_dir}/catalog.html"

        session = HTMLSession()
        r = session.get(model_catalog)
        file = ""
        for tt in r.html.find("tt"):
            file = tt.text
            if (gcm_var in file) and (scenario.value in file):
                if (model.value == "CanESM5") and (canesm5_run.value not in file):
                    continue
                break
        gcm_file = f"{thredds_base}/storage/data/climate/downscale/{technique_dir}/CMIP6_{technique.value}/{model_dir}/{file}"

    obs_file = f"{thredds_base}/storage/data/climate/PRISM/dataportal/{obs_var}_monClim_PRISM_historical_run1_198101-201012.nc"
    gcm_dataset = Dataset(gcm_file)
    obs_dataset = Dataset(obs_file)

    # Obtain the datasets' latitudes and longitudes to determine the subdomains
    gcm_lats = gcm_dataset.variables["lat"][:]
    gcm_lons = gcm_dataset.variables["lon"][:]
    obs_lats = obs_dataset.variables["lat"][:]
    obs_lons = obs_dataset.variables["lon"][:]
    gcm_lat_indices = get_index_range(gcm_lats, m.lat_min_gcm, m.lat_max_gcm)
    gcm_lon_indices = get_index_range(gcm_lons, m.lon_min_gcm, m.lon_max_gcm)
    obs_lat_indices = get_index_range(obs_lats, m.lat_min_obs, m.lat_max_obs)
    obs_lon_indices = get_index_range(obs_lons, m.lon_min_obs, m.lon_max_obs)
    gcm_lat_range = f"[{gcm_lat_indices[0]}:{gcm_lat_indices[1]}]"
    gcm_lon_range = f"[{gcm_lon_indices[0]}:{gcm_lon_indices[1]}]"
    obs_lat_range = f"[{obs_lat_indices[0]}:{obs_lat_indices[1]}]"
    obs_lon_range = f"[{obs_lon_indices[0]}:{obs_lon_indices[1]}]"

    # Use full time range of PNWNAmet datasets, but user-specified range for CMIP6
    if dataset_name == "PNWNAmet":
        gcm_ntime = len(gcm_dataset.variables["time"][:])
        gcm_time_range = f"[0:{gcm_ntime - 1}]"
    else:
        gcm_time_range = get_time_range(gcm_dataset, period.value)
    
    obs_ntime = len(obs_dataset.variables["time"][:])
    obs_time_range = f"[0:{obs_ntime - 1}]"

    # Request a subset of each dataset based on the array indices for each subdomain
    gcm_subset_file = f"{gcm_file}?time{gcm_time_range},lat{gcm_lat_range},lon{gcm_lon_range},{gcm_var}{gcm_time_range}{gcm_lat_range}{gcm_lon_range}"
    obs_subset_file = f"{obs_file}?time{obs_time_range},lat{obs_lat_range},lon{obs_lon_range},climatology_bounds,crs,{obs_var}{obs_time_range}{obs_lat_range}{obs_lon_range}"

    # For downscaling CMIP6 in a future period, the baseline 1981-2010 period is also required for calibration.
    # Concatenate the baseline and future subsets, save to local temporary file, and downscale this file
    if dataset_name == "CMIP6" and period.value != "1950-2010":
        print(f"Concatenating 1981-2010 and {period.value} subsets of {gcm_var}")
        gcm_subset_file = concat_baseline_future(gcm_dataset, gcm_subset_file, gcm_time_range)
    
    # If tasmean is requested, compute it via finch using the tasmax and tasmin subsets
    if clim_vars.value == "tasmean":
        print("Computing tasmean at " + str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        gcm_var = "tasmean"
        tasmax_file = gcm_subset_file
        if dataset_name == "CMIP6" and period.value != "1950-2010":
            print(f"Concatenating 1981-2010 and {period.value} subsets of tasmin")
            tasmin_future_file = f"{gcm_file.replace('tasmax', 'tasmin')}?time{gcm_time_range},lat{gcm_lat_range},lon{gcm_lon_range},tasmin{gcm_time_range}{gcm_lat_range}{gcm_lon_range}"
            tasmin_file = concat_baseline_future(gcm_dataset, tasmin_future_file, gcm_time_range)
        else:
            tasmin_file = tasmax_file.replace("tasmax", "tasmin")
        print("Starting tasmean process")
        tasmean = finch.tg(tasmax=tasmax_file, tasmin=tasmin_file, output_name = "tasmean")
        while tasmean.isNotComplete():
            sleep(3)
        gcm_file = thredds_base + "/birdhouse_wps_outputs" + tasmean.get()[0].split("wpsoutputs")[1]
        gcm_subset_file = gcm_file
        print("Finished computing tasmean at " + str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")) + "\n")

    gcm_dataset.close()
    obs_dataset.close()
    
    # Put together the parameters for `chickadee.ci`.
    # In the case for `pr`, the `units_bool` parameter is set to `False` in order to avoid converting the PRISM's `mm` units to the PNWNAmet's `mm/day` units.
    # Note that `start_date` and `end_date` in the `chickadee_params` refer to the PRISM climatological period for calibration
    region_name = region.value.lower().replace(" ", "-")
    gcm_varname = "tg" if gcm_var == "tasmean" else gcm_var
    chickadee_params = {
        "gcm_file": gcm_subset_file,
        "obs_file": obs_subset_file,
        "gcm_varname": gcm_varname,
        "obs_varname": obs_var,
        "max_gb": 0.5,
        "start_date": date(1981, 1, 1),
        "end_date": date(2010, 12, 31),
    }
    if gcm_var in ["pr", "tg"]:
        chickadee_params["units_bool"] = False
        if gcm_var == "pr":
            chickadee_params["pr_units"] = "mm/day"
    if dataset_name == "PNWNAmet":
        chickadee_params[
            "out_file"
        ] = f"{gcm_var}_{dataset_name}_{region_name}_on-demand.nc"
    else:
        if not canesm5_run.disabled:
            chickadee_params[
                "out_file"
            ] = f"{gcm_var}_{dataset_name}_{technique.value}_{model.value}_{canesm5_run.value}_{scenario.value}_{period.value}_{region_name}_on-demand.nc"
        else:
            chickadee_params[
                "out_file"
            ] = f"{gcm_var}_{dataset_name}_{technique.value}_{model.value}_{scenario.value}_{period.value}_{region_name}_on-demand.nc"

    print(chickadee_params["gcm_file"])
    print(f"Downscaling subset of {gcm_file.split('/')[-1]}")
    approx_time = 13 if "PNWNAmet" in gcm_file else 12
    print(f"Approximate time to completion: {str(approx_time)} minutes")
    global downscaled_outputs
    downscaled_outputs[gcm_var].append(chickadee.ci(**chickadee_params))
    print()

def get_index_range(arr, min_val, max_val):
    """Compute the indices in an array that correspond to the array's values
    closest to desired min/max values."""
    min_index = np.argmin(np.abs(arr - min_val))
    max_index = np.argmin(np.abs(arr - max_val))
    return (min_index, max_index)


def get_output(resp):
    """Get the URL of the Chickaee/Finch output file for downloading."""
    if resp.isNotComplete():
        print("Process is not complete.")
    else:
        print(f"Process status: {resp.status}")
        print(f"Link to process output: {resp.get()[0].replace('dodsC', 'fileServer')}")


def output_to_dataset(resp):
    """Open Chickadee/Finch output via its THREDDS location using netCDF4.Dataset for further examination."""
    url = resp.get()[0]
    if "wpsoutputs" in url:
        thredds_url = thredds_base + "/birdhouse_wps_outputs" + url.split("wpsoutputs")[1]
    else:
        thredds_url = url.replace("fileServer", "dodsC")
    ds = Dataset(thredds_url)
    return ds

class DefaultResponse:
    def __init__(self, url):
        self.url = url
        self.status = "ProcessSucceeded"
        
    def get(self):
        return (self.url,)

    def isComplete(self):
        return True

    def isNotComplete(self):
        return False

def use_default_downscaled_outputs():
    global downscaled_outputs
    test_base = "/storage/data/projects/comp_support/daccs/test-data/chickadee_CI_outputs/"
    downscaled_outputs["pr"].append(DefaultResponse(thredds_base + test_base + "pr_PNWNAmet_target_198101-201012_on-demand.nc"))
    downscaled_outputs["tasmax"].append(DefaultResponse(thredds_base + test_base + "tasmax_PNWNAmet_target_198101-201012_on-demand.nc"))
    downscaled_outputs["tasmin"].append(DefaultResponse(thredds_base + test_base + "tasmin_PNWNAmet_target_198101-201012_on-demand.nc"))
    downscaled_outputs["tasmean"].append(DefaultResponse(thredds_base + test_base + "tasmean_PNWNAmet_target_198101-201012_on-demand.nc"))

def add_previous_downscaled_output(url):
    global downscaled_outputs
    filename = url.split("/")[-1]
    varname = filename.split("_")[0]
    resp = DefaultResponse(url)
    if resp in downscaled_outputs[varname]:
        print(f"{url} already in {varname} files to compute indices")
        return
    downscaled_outputs[varname].append(resp)
    print(f"Added {url} to {varname} files to compute indices")

def display_downscaled_outputs():
    global downscaled_output_box
    downscaled_display = []
    for var in downscaled_outputs.keys():
        if len(downscaled_outputs[var]) == 0:
            continue
        header = HTML(value=f"<b>{var}</b>", style=description_style)
        downscaled_display.append(header)
        for downscaled_output in downscaled_outputs[var]:
            if downscaled_output.isComplete():
                output_checkbox = Checkbox(description=downscaled_output.get()[0], style=description_style)
                output_checkbox.observe(handle_enable_indices)
                downscaled_display.append(output_checkbox)
    downscaled_output_box = VBox(children=downscaled_display)


##################### Functions for using finch to compute climate indices #####################################

def setup_checkboxes(indices):
    checkboxes = []
    for (index, process) in indices.items():
        if process == finch.prsn:
            checkboxes.append(HBox(children=[Checkbox(description=index, style=description_style, disabled=True)]))
        else:
            options = all_res[:]
            if "month" in getfullargspec(process).args:
                options.extend(months)
            if "season" in getfullargspec(process).args:
                options.extend(seasons)
            checkboxes.append(HBox(children=[Checkbox(description=index, style=description_style, disabled=True), Dropdown(options=options)]))
    return checkboxes
    

def same_downscaled_params(dataset1, dataset2):
    filename1 = dataset1.split("/")[-1]
    filename2 = dataset2.split("/")[-1]
    params1 = filename1.split("_")[1:] # Get information excluding variable name
    params2 = filename2.split("_")[1:]
    return params1 == params2

def handle_enable_indices(change):
    enable = []
    disable = [pr_checkboxes, tasmax_checkboxes, tasmin_checkboxes, tasmean_checkboxes, multivar_checkboxes[0:2], [multivar_checkboxes[-1]]]
    global downscaled_output_selected
    for elem in downscaled_output_box.children:
        if type(elem) != Checkbox:
            continue
        basename = elem.description.split("/")[-1]
        var = basename.split("_")[0]
        if not elem.value and elem in downscaled_output_selected[var]:
            downscaled_output_selected[var].remove(elem)
        if elem.value:
            if elem not in downscaled_output_selected[var]:
                downscaled_output_selected[var].append(elem)
            if var == "pr" and pr_checkboxes not in enable:
                enable.append(pr_checkboxes)
                disable.remove(pr_checkboxes)
            elif var == "tasmax" and tasmax_checkboxes not in enable:
                enable.append(tasmax_checkboxes)
                disable.remove(tasmax_checkboxes)
            elif var == "tasmin" and tasmin_checkboxes not in enable:
                enable.append(tasmin_checkboxes)
                disable.remove(tasmin_checkboxes)
            else:
                enable.append(tasmean_checkboxes)
                disable.remove(tasmean_checkboxes)

    for tasmax_selected in downscaled_output_selected["tasmax"]:
        for tasmin_selected in downscaled_output_selected["tasmin"]:
            if same_downscaled_params(tasmax_selected.description, tasmin_selected.description) and multivar_checkboxes[0:2] not in enable:
                enable.append(multivar_checkboxes[0:2])
                disable.remove(multivar_checkboxes[0:2]) 
        for pr_selected in downscaled_output_selected["pr"]:
            if same_downscaled_params(tasmax_selected.description, pr_selected.description) and [multivar_checkboxes[-1]] not in enable:
                enable.append([multivar_checkboxes[-1]])
                disable.remove([multivar_checkboxes[-1]])      
                
    for boxes in enable:
        for box in boxes:
            box.children[0].disabled = False
    for boxes in disable:
        for box in boxes:
            box.children[0].disabled = True

output_widget_indices = Output()

@output_widget_indices.capture()
def compute_indices(downscaled_outputs_thredds, indices, checkboxes):
    global index_outputs
    for (process, box) in zip(indices, checkboxes):
        (selected, res) = (box.children[0].value, box.children[1].value)
        if selected:
            params = setup_index_process_params(process, res)
            print(f"Computing {box.children[0].description} from {(' and ').join(downscaled_outputs_thredds)}.")
            index_output = process(*downscaled_outputs_thredds, **params)
            index_outputs.append(index_output)

def setup_index_process_params(process, res):
    params = {}
    if res == "Monthly":
        params["freq"] = "MS"
        end = "monthly"
    elif res == "Seasonal":
        params["freq"] = "QS-DEC"
        end = "seasonal"
    else:
        params["freq"] = "YS"
        if res in months:
            params["month"] = months.index(res) + 1
            end = res[:3].lower()
        elif res in seasons:
            params["season"] = res.split("-")[1]
            end = params["season"].lower()
        else:
            end = "annual"

    index_output_names = {finch.sdii: "sdii", finch.cdd: "cdd", finch.cwd: "cwd", finch.wet_prcptot: "wet_prcptot",
                         finch.ice_days: "ice_days", finch.tx_max: "tx_max", finch.tx_min: "tx_min",
                         finch.frost_days: "frost_days", finch.tn_max: "tn_max", finch.tn_min: "tn_min",
                         finch.growing_season_length: "growing_season_length", finch.cooling_degree_days: "cooling_degree_days",
                         finch.freezing_degree_days: "freezing_degree_days", finch.growing_degree_days: "growing_degree_days",
                         finch.heating_degree_days: "heating_degree_days", finch.dtr: "dtr", finch.freezethaw_spell_frequency: "freezethaw_days", finch.prsn: "prsn",
                         }
    if process in index_output_names.keys():
        params.update({"output_name": index_output_names[process]})
        if process == finch.growing_degree_days:
            params.update({"thresh": "18 degC"})
        elif process == finch.heating_degree_days:
            params.update({"thresh": "5 degC"})
        elif process == finch.prsn:
            params.update({"method": "auer"})

    elif process == finch.max_n_day_precipitation_amount:
        params.update({"window": int(rxnday.value.split(" ")[0]), "output_name": "rx" + rxnday.value.split(" ")[0] + "day"})
    elif process == finch.wetdays:
        params.update({"thresh": rnnmm.value, "output_name": "r" + rnnmm.value.split(" ")[0] + "mm"})
    elif process == finch.tx_days_above:
        params.update({"thresh": summer_days.value, "output_name": "summer_days_" + summer_days.value.split(" ")[0] + "C"})
    else:
        params.update({"thresh": tropical_nights.value, "output_name": "tropical_nights_" + tropical_nights.value.split(" ")[0] + "C"})

    params["output_name"] += "_" + end
    return params
        
def handle_calc_indices(arg):
    # Get THREDDS location of downscaled output to pass to Finch
    for var in downscaled_output_selected.keys():
        for downscaled_output_checkbox in downscaled_output_selected[var]:
            if "wpsoutputs" in downscaled_output_checkbox.description:
                downscaled_output_thredds = thredds_base + "/birdhouse_wps_outputs" + downscaled_output_checkbox.description.split("wpsoutputs")[1]
            else:
                downscaled_output_thredds = downscaled_output_checkbox.description
            if var == "pr":
                compute_indices([downscaled_output_thredds], pr_indices.values(), pr_checkboxes)
            elif var == "tasmax":
                compute_indices([downscaled_output_thredds], tasmax_indices.values(), tasmax_checkboxes)
            elif var == "tasmin":
                compute_indices([downscaled_output_thredds], tasmin_indices.values(), tasmin_checkboxes)
            else:
                compute_indices([downscaled_output_thredds], tasmean_indices.values(), tasmean_checkboxes)

    for tasmax_selected in downscaled_output_selected["tasmax"]:
        tasmax_output_thredds = thredds_base + "/birdhouse_wps_outputs" + tasmax_selected.description.split("wpsoutputs")[1]
        region = tasmax_output_thredds.split("_")[-2] # URL is of the form <thredds_base>/birdhouse_wps_outputs/<process_id>/<filename>
        # where <filename> is of the form <var>_<dataset>_<CMIP6_params>_<period>_<region>_on-demand.nc
        for tasmin_selected in downscaled_output_selected["tasmin"]:
            tasmin_output_thredds = thredds_base + "/birdhouse_wps_outputs" + tasmin_selected.description.split("wpsoutputs")[1]
            if same_downscaled_params(tasmax_output_thredds, tasmin_output_thredds):
                compute_indices([tasmin_output_thredds, tasmax_output_thredds], list(multivar_indices.values())[0:2], multivar_checkboxes[0:2])
        for pr_selected in downscaled_output_selected["pr"]:
            pr_output_thredds = thredds_base + "/birdhouse_wps_outputs" + pr_selected.description.split("wpsoutputs")[1]
            if same_downscaled_params(tasmax_output_thredds, pr_output_thredds):
                compute_indices([pr_output_thredds, tasmax_output_thredds], [list(multivar_indices.values())[-1]], [multivar_checkboxes[-1]])                
            
def use_default_index_outputs():
    global index_outputs
    test_base = "/storage/data/projects/comp_support/daccs/test-data/finch_outputs/"
    index_outputs.append(DefaultResponse(thredds_base + test_base + "rx1day.nc"))
    index_outputs.append(DefaultResponse(thredds_base + test_base + "ice_days.nc"))
    index_outputs.append(DefaultResponse(thredds_base + test_base + "tn_max.nc"))

    
####################### Initialize interactive map and associated widgets ##################################

description_style = {'description_width': 'initial'}

mapnik = basemap_to_tiles(basemaps.OpenStreetMap.Mapnik)
mapnik.base = True
mapnik.name = "Default"

m = Map(
    basemap=mapnik,
    center=(53.5, -120),
    zoom=5,
    layout=Layout(height="600px"),
)
m.on_interaction(handle_interact)
m.center_point = ()

legend = LegendControl(
    {"GCM": "blue", "Obs": "red"}, name="Subdomains", position="topright"
)
m.add_control(legend)

center_hover = Text(value="", placeholder="")
center = Text(value="", placeholder="", description="Center:")
region = Text(value="", placeholder="", description="Region name:", style=description_style)
clim_vars = RadioButtons(
    options=["pr", "tasmax", "tasmin", "tasmean"], description="Climate variable:"
)
dataset = RadioButtons(options=["PNWNAmet (1945-2012)", "CMIP6 (1950-2100)"], description="Dataset:")
dataset.observe(handle_dataset_change)

technique = RadioButtons(
    options=["BCCAQv2", "MBCn"],
    description="CMIP6 downscaling technique:",
    disabled=True,
)
model = Dropdown(options=get_models(), description="CMIP6 model:", disabled=True)
model.style.description_width = "100px"
model.observe(handle_model_change)

canesm5_runs = ["r" + str(r) + "i1p2f1" for r in range(1, 11)]
canesm5_run = Dropdown(options=canesm5_runs, description="CanESM5 run:", disabled=True)
canesm5_run.style.description_width = "100px"

scenario = RadioButtons(
    options=[("SSP1-2.6", "ssp126"), ("SSP2-4.5", "ssp245"), ("SSP5-8.5", "ssp585")],
    description="CMIP6 emissions scenario:",
    disabled=True,
)
period = RadioButtons(
    options=["1950-2010", "2011-2040", "2041-2070", "2071-2100"], description="CMIP6 downscaled period:", disabled=True
)

run_downscaling = Button(
    description="Run Downscaling",
    button_style="success",
    disabled=False,
    tooltip="Click 'Run' to start the on-demand downscaling",
)
run_downscaling.on_click(handle_run_downscaling)

box_layout = Layout(
    display="flex", flex_flow="column", width="110%", align_items="center"
)
control_box_downscaling = Box(
    children=[
        center_hover,
        center,
        region,
        clim_vars,
        dataset,
        technique,
        model,
        canesm5_run,
        scenario,
        period,
        run_downscaling,
    ],
    layout=box_layout,
)


############################### Initialize widgets for computing climate indices ###################################

downscaled_output_box = None
downscaled_output_selected = {"pr": [], "tasmax": [], "tasmin": [], "tasmean": []}

all_res = ["Annual", "Monthly", "Seasonal"]
months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
seasons = ["Winter-DJF", "Spring-MAM", "Summer-JJA", "Fall-SON"]

rxnday = SelectionSlider(options=["1 day"] + [str(i) + " days" for i in range(2,11)], value="1 day")
rnnmm = SelectionSlider(options=[str(i) + " mm/day" for i in range(1,31)], value="10 mm/day")
pr_indices = {"Max N-day Precip Amount": finch.max_n_day_precipitation_amount,
              "Simple Precip Intensity Index": finch.sdii,
              "Days with Precip over N-mm": finch.wetdays,
              "Maximum Length of Dry Spell": finch.cdd,
              "Maximum Length of Wet Spell": finch.cwd,
              "Total Wet-Day Precip": finch.wet_prcptot,
             }
pr_header = HTML(value="<b>Precipitation Indices</b>", style=description_style)
pr_checkboxes = setup_checkboxes(pr_indices)
pr_box = VBox(children=[pr_header, pr_checkboxes[0], rxnday, *pr_checkboxes[1:3], rnnmm, *pr_checkboxes[3:]])

summer_days = SelectionSlider(options=[str(i) + " degC" for i in range(20,31)], value="25 degC")
tasmax_indices = {"Summer Days": finch.tx_days_above,
                  "Ice Days": finch.ice_days,
                  "Hottest Day": finch.tx_max,
                  "Coldest Day": finch.tx_min,
                 }
tasmax_header = HTML(value="<b>Maximum Temperature Indices</b>", style=description_style)
tasmax_checkboxes = setup_checkboxes(tasmax_indices)
tasmax_box = VBox(children=[tasmax_header, tasmax_checkboxes[0], summer_days, *tasmax_checkboxes[1:]])

tropical_nights = SelectionSlider(options=[str(i) + " degC" for i in range(10,31)], value = "20 degC")
tasmin_indices = {"Frost Days": finch.frost_days,
                  "Tropical Nights": finch.tropical_nights,
                  "Hottest Night": finch.tn_max,
                  "Coldest Night": finch.tn_min,
                 }
tasmin_header = HTML(value="<b>Minimum Temperature Indices</b>", style=description_style)
tasmin_checkboxes = setup_checkboxes(tasmin_indices)
tasmin_box = VBox(children=[tasmin_header, *tasmin_checkboxes[:2], tropical_nights, *tasmin_checkboxes[2:]])

tasmean_indices = {"Growing Season Length": finch.growing_season_length,
                   "Cooling Degree Days": finch.cooling_degree_days,
                   "Freezing Degree Days": finch.freezing_degree_days,
                   "Growing Degree Days": finch.growing_degree_days,
                   "Heating Degree Days": finch.heating_degree_days,
                  }
tasmean_header = HTML(value="<b>Mean Temperature Indices</b>", style=description_style)
tasmean_checkboxes = setup_checkboxes(tasmean_indices)
tasmean_box = VBox(children=[tasmean_header, *tasmean_checkboxes])

multivar_indices = {"Daily Temperature Range": finch.dtr,
                    "Freeze-Thaw Days": finch.freezethaw_spell_frequency,
                    "Precip as Snow": finch.prsn,
                   }
multivar_header = HTML(value="<b>Multivariate Indices</b>", style=description_style)
multivar_checkboxes = setup_checkboxes(multivar_indices)
multivar_box = VBox(children=[multivar_header, *multivar_checkboxes])

indices = HBox(children=[pr_box, tasmax_box, tasmin_box, tasmean_box, multivar_box])

calc_indices = Button(
    description="Calculate Indices",
    button_style="info",
    disabled=False,
    tooltip="Click 'Run' to start the climate index calculations",
)
calc_indices.on_click(handle_calc_indices)