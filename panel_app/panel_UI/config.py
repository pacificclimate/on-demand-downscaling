import os
from birdy import WPSClient
from datetime import date
from dotenv import load_dotenv
import os

load_dotenv()

MAGPIE_URL = os.getenv("MAGPIE_URL")
BIRDHOUSE_HOST_URL = os.getenv("BIRDHOUSE_HOST_URL")

CHICKADEE_URL = f"{BIRDHOUSE_HOST_URL.replace('https','http')}:30102"
FINCH_URL = f"{BIRDHOUSE_HOST_URL}/twitcher/ows/proxy/finch/wps"
THREDDS_BASE = f"{BIRDHOUSE_HOST_URL}/twitcher/ows/proxy/thredds/dodsC/datasets"
THREDDS_CATALOG = f"{BIRDHOUSE_HOST_URL}/twitcher/ows/proxy/thredds/catalog/datasets"

chickadee = WPSClient(CHICKADEE_URL, progress=True)
finch = WPSClient(FINCH_URL, progress=True)

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
SCENARIOS = [("SSP1-2.6", "ssp126"), ("SSP2-4.5", "ssp245"), ("SSP5-8.5", "ssp585")]
PERIODS = ["1950-2010", "1981-2100", "1950-2100"]

TECHNIQUE_MAP = {
    "Univariate": "BCCAQv2",
    "Multivariate": "MBCn",
}

DATASET_MAP = {
    "PCIC-Blend": "PNWNAmet",
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
SUMMER_DAY_THRESHOLD_OPTIONS = [f"{i} degC" for i in range(20, 31)]
TROPICAL_NIGHTS_THRESHOLD_OPTIONS = [f"{i} degC" for i in range(10, 31)]
# --- Time Window Defaults ---
DEFAULT_START_DATE = date(1981, 1, 1)
DEFAULT_END_DATE = date(2010, 12, 31)

INDEX_FUNCTIONS_STRUCTURE = {
    "pr": [
        ("Max N-day Precip Amount", "max_n_day_precipitation_amount"),
        ("Simple Precip Intensity Index", "sdii"),
        ("Days with Precip over N-mm", "wetdays"),
        ("Maximum Length of Dry Spell", "cdd"),
        ("Maximum Length of Wet Spell", "cwd"),
        ("Total Wet-Day Precip", "wet_prcptot"),
    ],
    "tasmax": [
        ("Summer Days", "tx_days_above"),
        ("Ice Days", "ice_days"),
        ("Hottest Day", "tx_max"),
        ("Coldest Day", "tx_min"),
    ],
    "tasmin": [
        ("Frost Days", "frost_days"),
        ("Tropical Nights", "tropical_nights"),
        ("Hottest Night", "tn_max"),
        ("Coldest Night", "tn_min"),
    ],
    "tasmean": [
        ("Growing Season Length", "growing_season_length"),
        ("Cooling Degree Days", "cooling_degree_days"),
        ("Freezing Degree Days", "freezing_degree_days"),
        ("Growing Degree Days", "growing_degree_days"),
        ("Heating Degree Days", "heating_degree_days"),
    ],
    "multivar": [
        ("Daily Temperature Range", "dtr"),
        ("Freeze-Thaw Days", "freezethaw_spell_frequency"),
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
        "output_prefix": "summer_days_{thresh}C",
        "param_key": "thresh",
        "threshold_parser": lambda s: s,
    },
    "tropical_nights": {
        "output_prefix": "tropical_nights_{thresh}C",
        "param_key": "thresh",
        "threshold_parser": lambda s: s,
    },
    "growing_degree_days": {
        "output_prefix": "gdd",
        "param_key": "thresh",
        "param_overrides": {"thresh": "18 degC"},
    },
    "heating_degree_days": {
        "output_prefix": "hdd",
        "param_key": "thresh",
        "param_overrides": {"thresh": "5 degC"},
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
    "summer_days",
    "tropical_nights",
    "index_states",
    "center_point",
    "selected_variables",
    "indices_selected",
    "email",
]
