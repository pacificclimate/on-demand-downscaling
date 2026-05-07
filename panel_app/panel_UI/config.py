import os
from birdy import WPSClient
from datetime import date
from dotenv import load_dotenv
import os

load_dotenv()

APP_NAME = "Canada-wide On-Demand fine-scale DownScaling Application"
SERVICE_CHECK_TIMEOUT = 60
SERVICE_STATUS_TTL_SECONDS = 30

MAGPIE_URL = os.getenv("MAGPIE_URL")
BIRDHOUSE_PUB_URL = os.getenv("BIRDHOUSE_PUB_URL")
BIRDHOUSE_FQDN = os.getenv("BIRDHOUSE_FQDN")
CHICKADEE_URL = f"{BIRDHOUSE_PUB_URL}/twitcher/ows/proxy/chickadee/wps"
FINCH_URL = f"{BIRDHOUSE_PUB_URL}/twitcher/ows/proxy/finch/wps"
THREDDS_BASE = f"{BIRDHOUSE_FQDN}/twitcher/ows/proxy/thredds/dodsC/datasets"
THREDDS_CATALOG = f"{BIRDHOUSE_FQDN}/twitcher/ows/proxy/thredds/catalog/datasets"

chickadee = WPSClient(CHICKADEE_URL, progress=True)
finch = WPSClient(FINCH_URL, progress=True)


PRISM_URL = f"{THREDDS_BASE}/storage/data/climate/PRISM/dataportal/pr_monClim_PRISM_historical_run1_198101-201012.nc"
CANADA_MOSAIC_URL = f"{THREDDS_BASE}/storage/data/climate/observations/gridded/Canada_mosaic_30arcsec/pr_monClim_Canada_mosaic_30arcsec_198101-201012.nc"


def pcic_blend_url(gcm_var):
    return f"{THREDDS_BASE}/storage/data/climate/observations/gridded/PCIC_Blend/diagonal/{gcm_var}_day_PCIC_Blended_Observations_v1_1950-2012.nc"


def cmip6_url(tech_dir, internal_tech, model_dir, name):
    return f"{THREDDS_BASE}/storage/data/climate/downscale/{tech_dir}/CMIP6_{internal_tech}/{model_dir}/{name}"


def cmip6_catalog_url(tech_dir, internal_tech, model_dir):
    return f"{THREDDS_CATALOG}/storage/data/climate/downscale/{tech_dir}/CMIP6_{internal_tech}/{model_dir}/catalog.xml"


def bccaq2_catalog_url():
    return f"{THREDDS_CATALOG}/storage/data/climate/downscale/BCCAQ2/CMIP6_BCCAQv2/catalog.xml"


def canada_mosaic_url(obs_var):
    return f"{THREDDS_BASE}/storage/data/climate/observations/gridded/Canada_mosaic_30arcsec/{obs_var}_monClim_Canada_mosaic_30arcsec_198101-201012.nc"


SHOW_OBS_DOMAIN = True  # Temp for RCI to compare Canada vs BC PRISM
label_map = {
    "center_point": "Location on the map",
    "region": "Study Area",
    "selected_variables": "Climate Variable",
    "technique": "Technique",
    "model": "Model",
    "scenario": "Scenario",
    "period": "Period",
    "canesm5_run": "CanESM5 Run",
}


# --- Climate Vars and Params ---
CLIM_VARS = {
    "pr": "pr",
    "tasmax": "tmax",
    "tasmin": "tmin",
    "tasmean": "tas",
}

CANE5_RUNS = [f"r{i}i1p2f1" for i in range(1, 11)]
CANE5_RUNS_SSP370_MULTIVAR = ["r1i1p2f1"]

BASE_SCENARIOS = [
    ("SSP1-2.6", "ssp126"),
    ("SSP2-4.5", "ssp245"),
    ("SSP5-8.5", "ssp585"),
]

SSP370 = ("SSP3-7.0", "ssp370")


PERIODS = ["1950-2010", "1981-2100", "1950-2100"]

TECHNIQUE_MAP = {
    "Univariate": "BCCAQv2",
    "Multivariate": "MBCn",
}

DATASET_MAP = {
    "PCIC-Blend": "PCIC-Blend",
    "CanDCS": "CMIP6",
}


@property
def internal_technique(self):
    return self.TECHNIQUE_MAP.get(self.technique, self.technique)


@property
def internal_dataset(self):
    return self.DATASET_MAP.get(self.dataset, self.dataset)


# --- Resolutions and Temporal Groupings ---
RESOLUTIONS = ["Annual", "Monthly", "Seasonal"]
MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]
SEASONS = ["Winter-DJF", "Spring-MAM", "Summer-JJA", "Fall-SON"]

# --- Default UI Settings ---
DEFAULT_MAP_CENTER = (53.5, -120)
DEFAULT_MAP_ZOOM = 5
DEFAULT_LAYOUT_WIDTH = "75%"

# --- Limits ---
MAX_SELECTED_INDICES = 8

# --- Threshold Slider Defaults ---
N_DAY_PRECIP_OPTIONS = ["1 day"] + [f"{i} days" for i in range(2, 11)]
WETDAY_THRESHOLD_OPTIONS = [f"{i} mm/day" for i in range(1, 31)]
PRECIP_PERCENTILE_OPTIONS = [f"{i} pct" for i in range(0, 100)]
PRECIP_THRESHOLD_OPTIONS = [f"{i} mm/day" for i in range(1, 31)]
TX_DAYS_ABOVE_THRESHOLD_OPTIONS = [f"{i} degC" for i in range(20, 36)]
TN_DAYS_ABOVE_THRESHOLD_OPTIONS = [f"{i} degC" for i in range(10, 31)]
TN_DAYS_BELOW_THRESHOLD_OPTIONS = [f"{i} degC" for i in range(-30, 1)]
HDD_THRESHOLD_OPTIONS = [f"{i} degC" for i in range(10, 21)]
CDD_THRESHOLD_OPTIONS = [f"{i} degC" for i in range(10, 21)]
COLD_SPELL_THRESHOLD_OPTIONS = [f"{i} degC" for i in range(-20, -9)]
COLD_SPELL_N_DAY_OPTIONS = ["2 days"] + [f"{i} days" for i in range(3, 11)]
CWD_THRESHOLD_OPTIONS = [f"{i} mm/day" for i in range(1, 31)]
CDD_DRY_THRESHOLD_OPTIONS = [f"{i} mm/day" for i in range(1, 4)]
HEAT_WAVE_TN_THRESHOLD_OPTIONS = [f"{i} degC" for i in range(10, 31)]
HEAT_WAVE_TX_THRESHOLD_OPTIONS = [f"{i} degC" for i in range(20, 36)]
HEAT_WAVE_N_DAY_OPTIONS = ["2 days"] + [f"{i} days" for i in range(3, 11)]
# --- Time Window Defaults ---
DEFAULT_START_DATE = date(1981, 1, 1)
DEFAULT_END_DATE = date(2010, 12, 31)

INDEX_FUNCTIONS_STRUCTURE = {
    "tasmax": [
        ("Mean TX", "tx_mean"),
        ("Ice Days", "ice_days"),
        ("Hottest Day", "tx_max"),
        ("Coldest Day", "tx_min"),
        ("Days Above a Specified TX", "tx_days_above"),
    ],
    "tasmin": [
        ("Mean TN", "tn_mean"),
        ("Hottest Night", "tn_max"),
        ("Coldest Night", "tn_min"),
        ("Frost Days", "frost_days"),
        ("Days Above a Specified TN", "tn_days_above"),
        ("Days Below a Specified TN", "tn_days_below"),
    ],
    "tasmean": [
        ("Mean TM", "tg_mean"),
        ("Growing Season Length", "growing_season_length"),
        ("Growing Degree Days", "growing_degree_days"),
        ("Freezing Degree Days", "freezing_degree_days"),
        ("Heating Degree Days", "heating_degree_days"),
        ("Cooling Degree Days", "cooling_degree_days"),
        ("Cold Spell Days", "cold_spell_days"),
    ],
    "pr": [
        ("Max N-day Precip Amount", "max_n_day_precipitation_amount"),
        ("Total Precipitation", "prcptot"),
        ("Average Wet-Day Precipitation (SDII)", "sdii"),
        ("Days with Precip over N-mm", "wetdays"),
        (
            "Days Over Precip Percentile Threshold",
            "days_over_precip_thresh",
        ),
        ("Maximum Length of Wet Spell", "cwd"),
        ("Maximum Length of Dry Spell", "cdd"),
    ],
    "multivar": [
        ("Extreme Temperature Range", "etr"),
        ("Freeze-Thaw Days", "dlyfrzthw"),
        ("Snowfall", "prsn"),
        ("Rainfall", "prlp"),
        ("Heat Wave Days", "heat_wave_index"),
        ("Heat Wave Number", "heat_wave_frequency"),
        ("Heat Wave Maximum Length", "heat_wave_max_length"),
    ],
}

INDEX_PROCESS_CONFIG = {
    "max_n_day_precipitation_amount": {
        "output_prefix": "rx{window}day",
        "param_key": "window",
        "threshold_parser": lambda s: int(s.split(" ")[0]),
    },
    "wetdays": {
        "output_prefix": "r{num}mm",
        "param_key": "thresh",
        "threshold_parser": lambda s: s,  # Finch param: "10 mm/day"
        "number_parser": lambda s: s.split(" ")[0],  # Filename: "10"
    },
    "tx_days_above": {
        "output_prefix": "tx_days_above_{thresh}C",
        "param_key": "thresh",
        "threshold_parser": lambda s: s,
    },
    "tn_days_above": {
        "output_prefix": "tn_days_above_{thresh}C",
        "param_key": "thresh",
        "threshold_parser": lambda s: s,
    },
    "tn_days_below": {
        "output_prefix": "tn_days_below_{thresh}C",
        "param_key": "thresh",
        "threshold_parser": lambda s: s,
    },
    "cdd": {
        "output_prefix": "cdd_{num}mmday",
        "param_key": "thresh",
        "threshold_parser": lambda s: s,
        "number_parser": lambda s: s.split(" ")[0],
    },
    "cwd": {
        "output_prefix": "cwd_{num}mmday",
        "param_key": "thresh",
        "threshold_parser": lambda s: s,
        "number_parser": lambda s: s.split(" ")[0],
    },
    "sdii": {
        "output_prefix": "sdii",
        "param_key": "thresh",
        "param_overrides": {"thresh": "1 mm/day"},
    },
    "days_over_precip_thresh": {
        "output_prefix": "days_over_precip_thresh",
        "param_key": "thresh",
        "threshold_parser": lambda t: {
            "thresh": t.get("thresh", "1 mm/day"),
        },
    },
    "cooling_degree_days": {
        "output_prefix": "cdd_{thresh}C",
        "param_key": "thresh",
        "threshold_parser": lambda s: s,
    },
    "growing_degree_days": {
        "output_prefix": "gdd",
        "param_key": "thresh",
        "param_overrides": {"thresh": "18 degC"},
    },
    "heating_degree_days": {
        "output_prefix": "hdd_{thresh}C",
        "param_key": "thresh",
        "threshold_parser": lambda s: s,
    },
    "cold_spell_days": {
        "output_prefix": "cold_spell_{thresh}_{window}",
        "threshold_parser": lambda t: {
            "thresh": t.get("thresh"),
            "window": int(t.get("window", "2 days").split(" ")[0]),
        },
    },
    "prsn": {
        "output_prefix": "snowfall",
        "param_overrides": {"method": "auer"},
    },
    "prlp": {
        "output_prefix": "rainfall",
        "param_overrides": {"method": "auer"},
    },
    "heat_wave_frequency": {
        "output_prefix": "heat_wave_frequency_{thresh_tasmin}_{thresh_tasmax}_{window}d",
        "threshold_parser": lambda t: {
            "thresh_tasmin": t.get("tn_thresh"),
            "thresh_tasmax": t.get("tx_thresh"),
            "window": int(t.get("window", "2 days").split(" ")[0]),
        },
    },
    "heat_wave_index": {
        "output_prefix": "heat_wave_days_{thresh}_{window}d",
        "threshold_parser": lambda t: {
            "thresh": t.get("tx_thresh"),
            "window": int(t.get("window", "2 days").split(" ")[0]),
        },
    },
    "heat_wave_max_length": {
        "output_prefix": "heat_wave_max_length_{thresh_tasmin}_{thresh_tasmax}_{window}d",
        "threshold_parser": lambda t: {
            "thresh_tasmin": t.get("tn_thresh"),
            "thresh_tasmax": t.get("tx_thresh"),
            "window": int(t.get("window", "2 days").split(" ")[0]),
        },
    },
    "*": {
        "param_key": "thresh",
        "output_prefix": None,
    },
}


PARAMS_TO_WATCH = [
    "center_hover",
    "center",
    "region",
    "map_bounds",
    "pr",
    "tasmax",
    "tasmin",
    "tasmean",
    "dataset",
    "technique",
    "canesm5_run",
    "model",
    "scenario",
    "period",
    "output_intent",
    "rxnday",
    "rnnmm",
    "precip_percentile",
    "precip_thresh",
    "tx_days_above_thresh",
    "tn_days_above_thresh",
    "tn_days_below_thresh",
    "hdd_thresh",
    "cdd_thresh",
    "cold_spell_thresh",
    "cold_spell_window",
    "cwd_thresh",
    "cdd_dry_thresh",
    "heat_wave_tn_thresh",
    "heat_wave_tx_thresh",
    "heat_wave_window",
    "index_states",
    "center_point",
    "selected_variables",
    "indices_selected",
    "email",
]
