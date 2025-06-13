import os
import requests
import numpy as np
from birdy import WPSClient
import ipywidgets as widgets
from ipywidgets import (
    Output,
    Layout,
    Box,
    HBox,
    VBox,
    SelectionSlider,
    Checkbox,
    Dropdown,
    RadioButtons,
    Button,
    HTML,
    Text,
)
from ipyleaflet import (
    Map,
    LayerGroup,
    Rectangle,
    basemap_to_tiles,
    basemaps,
    Marker,
    LegendControl,
)
import panel as pn

from helpers import (
    in_bc,
    get_subdomain,
    get_models,
    get_time_range,
    get_index_range,
    concat_baseline_future,
    find_cancel_button,
    get_output,
    output_to_dataset,
    add_previous_downscaled_outputs,
    display_downscaled_outputs,
    setup_index_checkboxes,
    check_same_downscaled_params,
    setup_index_process_params,
    get_output_thredds_location,
)

# Enable Panel extensions for ipywidgets and leaflet
pn.extension("ipywidgets", "leaflet")

# Instantiate the WPS clients
host = os.getenv("BIRDHOUSE_HOST_URL", "https://marble-dev01.pcic.uvic.ca")
chickadee = WPSClient(f"{host.replace('https','http')}:30102", progress=True)
finch = WPSClient(f"{host}/twitcher/ows/proxy/finch/wps", progress=True)

# Globals for tracking outputs
downscaled_outputs = {"pr": [], "tasmax": [], "tasmin": [], "tasmean": []}
index_outputs = []


thredds_base = f"{host}/twitcher/ows/proxy/thredds/dodsC/datasets"
thredds_catalog = f"{host}/twitcher/ows/proxy/thredds/catalog/datasets"

# Output panes for Panel
output_widget_downscaling = Output()
output_widget_indices = Output()


# # ---------------- Dynamic index panel based on loaded outputs ----------------
# def build_indices_panel():
#     """
#     Construct an HBox of only those index boxes for which downscaled_outputs[var] is non-empty,
#     followed by the Calculate Indices button.
#     """
#     panels = []
#     mapping = {
#         "pr": pr_box,
#         "tasmax": tasmax_box,
#         "tasmin": tasmin_box,
#         "tasmean": tasmean_box,
#         "multivar": multivar_box,
#     }
#     for var, box in mapping.items():
#         if downscaled_outputs.get(var):
#             panels.append(box)
#     # always include calculate button at end
#     panels.append(calc_indices)
#     return HBox(panels)


def create_map_ui():
    import os
    import panel as pn
    from birdy import WPSClient
    from ipywidgets import (
        Output,
        Layout,
        Box,
        HBox,
        VBox,
        SelectionSlider,
        Checkbox,
        Dropdown,
        RadioButtons,
        Button,
        HTML,
        Text,
    )
    from ipyleaflet import (
        Map,
        LayerGroup,
        Rectangle,
        basemap_to_tiles,
        basemaps,
        Marker,
        LegendControl,
    )
    from helpers import in_bc, get_subdomain, get_models, setup_index_checkboxes

    log_messages = []
    log_output = pn.pane.Str("", sizing_mode="stretch_width")

    def log(message):
        log_messages.append(message)
        log_output.object = "\n".join(log_messages[-3:])  # show last 3 lines

    def handle_dataset_change(change):
        """Enable/disable the widgets that set the
        CMIP6 parameters depending on if
        CMIP6/PNWNAmet is selected."""
        technique.disabled = not technique.disabled
        model.disabled = not model.disabled
        scenario.disabled = not scenario.disabled
        period.disabled = not period.disabled

    def handle_model_change(change):
        """Enable/disable the CanESM5
        run selector depending on if
        CanESM5 is/is not the selected model."""
        if model.value == "CanESM5":
            canesm5_run.disabled = False
        else:
            canesm5_run.disabled = True

    pn.extension("ipywidgets", "leaflet")

    # Instantiate the WPS client
    host = os.getenv("BIRDHOUSE_HOST_URL", "https://marble-dev01.pcic.uvic.ca")
    finch = WPSClient(f"{host}/twitcher/ows/proxy/finch/wps", progress=True)

    # Output widgets
    output_widget_downscaling = Output()
    output_widget_indices = Output()

    # Map setup
    sub_layers = LayerGroup()
    mapnik = basemap_to_tiles(basemaps.OpenStreetMap.Mapnik)
    mapnik.base = True
    m = Map(basemap=mapnik, center=(53.5, -120), zoom=5, layout=Layout(height="600px"))
    legend = LegendControl(
        {"GCM": "blue", "Obs": "red"}, name="Subdomains", position="topright"
    )
    m.add_control(legend)
    m.add_layer(sub_layers)
    # ---------------- Downscaling Controls ----------------
    description_style = {"description_width": "initial"}
    center_hover = Text(placeholder="Coordinates")
    center = Text(description="Center:")
    region = Text(description="Region:", style=description_style)
    clim_vars = RadioButtons(
        options=["pr", "tasmax", "tasmin", "tasmean"], description="Variable:"
    )
    dataset = RadioButtons(options=["PNWNAmet", "CMIP6"], description="Dataset:")
    technique = RadioButtons(
        options=["BCCAQv2", "MBCn"], description="Technique:", disabled=True
    )
    canesm5_run = Dropdown(
        options=[f"r{i}i1p2f1" for i in range(1, 11)],
        description="CanESM5 run:",
        disabled=True,
    )
    model = Dropdown(options=get_models(), description="Model:", disabled=True)
    scenario = RadioButtons(
        options=[
            ("SSP1-2.6", "ssp126"),
            ("SSP2-4.5", "ssp245"),
            ("SSP5-8.5", "ssp585"),
        ],
        description="Scenario:",
        disabled=True,
    )
    period = RadioButtons(
        options=["1950-2010", "1981-2100", "1950-2100"],
        description="Period:",
        disabled=True,
    )
    run_downscaling = Button(description="Run Downscaling", button_style="success")

    def handle_run_downscaling(_):  # placeholder
        output_widget_downscaling.clear_output(wait=True)
        with output_widget_downscaling:
            if not getattr(m, "center_point", None):
                log("Select center point first.")
                return
            if not region.value.strip():
                log("Enter region name.")
                return
            log("Starting downscaling...")

    dataset.observe(handle_dataset_change)
    model.observe(handle_model_change)
    run_downscaling.on_click(handle_run_downscaling)

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
        layout=Layout(display="flex", flex_flow="column", width="100%"),
    )

    # ---------------- Map interaction ----------------
    def handle_interact(**kwargs):
        output_widget_downscaling.clear_output(wait=True)
        if kwargs.get("type") != "click" or "coordinates" not in kwargs:
            return
        with output_widget_downscaling:
            pt = (
                round(kwargs["coordinates"][0], 5),
                round(kwargs["coordinates"][1], 5),
            )
            center_hover.value = str(pt)

            if not in_bc(pt):
                log("Please select a point within BC.\n")

                return

            sub_layers.clear()
            if sub_layers in m.layers:
                m.remove_layer(sub_layers)

            m.center_point = pt
            center.value = str(pt)

            lat_min_obs, lat_max_obs = pt[0] - 1.25, pt[0] + 1.25
            lon_min_obs, lon_max_obs = pt[1] - 1.25, pt[1] + 1.25
            lat_min_gcm, lat_max_gcm = pt[0] - 1.5, pt[0] + 1.5
            lon_min_gcm, lon_max_gcm = pt[1] - 1.5, pt[1] + 1.5

            marker = Marker(location=pt, interactive=False, draggable=False)
            gcm_layer = get_subdomain(
                lat_min_gcm, lat_max_gcm, lon_min_gcm, lon_max_gcm, "blue", "GCM"
            )
            obs_layer = get_subdomain(
                lat_min_obs, lat_max_obs, lon_min_obs, lon_max_obs, "red", "Obs"
            )

            sub_layers.add_layer(marker)
            sub_layers.add_layer(gcm_layer)
            sub_layers.add_layer(obs_layer)
            m.add_layer(sub_layers)

    m.on_interaction(handle_interact)

    # ---------------- Indices ----------------
    index_functions = {
        "pr": {
            "Max N-day Precip Amount": finch.max_n_day_precipitation_amount,
            "Simple Precip Intensity Index": finch.sdii,
            "Days with Precip over N-mm": finch.wetdays,
            "Maximum Length of Dry Spell": finch.cdd,
            "Maximum Length of Wet Spell": finch.cwd,
            "Total Wet-Day Precip": finch.wet_prcptot,
        },
        "tasmax": {
            "Summer Days": finch.tx_days_above,
            "Ice Days": finch.ice_days,
            "Hottest Day": finch.tx_max,
            "Coldest Day": finch.tx_min,
        },
        "tasmin": {
            "Frost Days": finch.frost_days,
            "Tropical Nights": finch.tropical_nights,
            "Hottest Night": finch.tn_max,
            "Coldest Night": finch.tn_min,
        },
        "tasmean": {
            "Growing Season Length": finch.growing_season_length,
            "Cooling Degree Days": finch.cooling_degree_days,
            "Freezing Degree Days": finch.freezing_degree_days,
            "Growing Degree Days": finch.growing_degree_days,
            "Heating Degree Days": finch.heating_degree_days,
        },
        "multivar": {
            "Daily Temperature Range": finch.dtr,
            "Freeze-Thaw Days": finch.freezethaw_spell_frequency,
        },
    }
    index_boxes = {
        var: setup_index_checkboxes(funcs) for var, funcs in index_functions.items()
    }

    pr_box = VBox(children=[HTML("<b>Precipitation Indices</b>")] + index_boxes["pr"])
    tasmax_box = VBox(
        children=[HTML("<b>Max Temp Indices</b>")] + index_boxes["tasmax"]
    )
    tasmin_box = VBox(
        children=[HTML("<b>Min Temp Indices</b>")] + index_boxes["tasmin"]
    )
    tasmean_box = VBox(
        children=[HTML("<b>Mean Temp Indices</b>")] + index_boxes["tasmean"]
    )
    multivar_box = VBox(
        children=[HTML("<b>Multivariate Indices</b>")] + index_boxes["multivar"]
    )
    calc_indices = Button(description="Calculate Indices", button_style="info")

    return pn.Column(
        pn.Row(
            pn.panel(m, sizing_mode="stretch_width"),
            pn.Column(control_box_downscaling, sizing_mode="fixed"),
        ),
        pn.Row(log_output),
        pn.Row(output_widget_downscaling, output_widget_indices),
        pn.Row(tasmax_box, tasmin_box, tasmean_box),
        pn.Row(pr_box, multivar_box),
        calc_indices,
    )
