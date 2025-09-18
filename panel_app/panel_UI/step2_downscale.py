import panel as pn
from ipyleaflet import Marker, LayerGroup
from .state import get_state, next_step, prev_step
from .widgets import (
    build_map,
    build_downscaling_controls,
    build_panel_continue_button,
)
from .user_warnings import user_warn, get_user_warning_pane
from .panel_helpers import (
    get_subdomain,
    in_canada,
    in_bc,
    get_models,
)
from .config import *


def apply_location_rules(pt, controls, state):
    """
    Returns True if the center point is inside Canada, else False.
    Also enforces BC rule:
      - outside BC: dataset -> CanDCS + disable widget (one-time warning)
      - inside BC:  re-enable dataset widget
    """

    if not in_canada(pt):
        user_warn("Please select a point within Canada.\n")
        return False

    doc = pn.state.curdoc
    inside = in_bc(pt)
    prev_inside = getattr(doc, "last_inside_bc", None)

    if not inside:
        # Force CanDCS when outside BC
        if controls["dataset"].value != "CanDCS":
            controls["dataset"].value = "CanDCS"
        controls["dataset"].disabled = True
        state.dataset = "CanDCS"
        # Warn once on transition outside-BC
        if prev_inside is True or prev_inside is None:
            user_warn("Outside BC: dataset locked to **CanDCS**.", "light")
    else:
        # Back in BC: allow switching again
        previously_outside = prev_inside is False
        controls["dataset"].disabled = False
        if previously_outside:
            user_warn("Back in BC: **PCIC-Blend** is available again.", "light")

    doc.last_inside_bc = inside
    return True


def shift_box(dx=0, dy=0):
    doc = pn.state.curdoc
    map_widget = getattr(doc, "map_widget", None)
    controls = getattr(doc, "controls", None)
    state = get_state()

    if not map_widget or not hasattr(map_widget, "center_point"):
        return

    # Move by full box (0.5°)
    lat, lon = map_widget.center_point
    new_pt = (lat + dy, lon + dx)
    if controls and not apply_location_rules(new_pt, controls, state):
        return
    state.center_point = new_pt

    if controls and "center" in controls:
        controls["center"].value = str(new_pt)

    if (
        hasattr(map_widget, "active_overlay")
        and map_widget.active_overlay in map_widget.layers
    ):
        map_widget.remove_layer(map_widget.active_overlay)

    # Add new overlay
    marker, gcm_layer, obs_layer, bounds = make_overlay_layers(new_pt)
    overlay_group = LayerGroup(layers=(marker, gcm_layer, obs_layer))
    map_widget.add_layer(overlay_group)
    map_widget.active_overlay = overlay_group
    map_widget.center_point = new_pt

    # Update map bounds
    state.map_bounds = bounds


def get_map_widget(force_new=False):
    doc = pn.state.curdoc
    if force_new or not hasattr(doc, "map_widget"):
        if hasattr(doc, "map_widget"):
            # Clean up existing map widget
            del doc.map_widget
        map_widget = build_map(DEFAULT_MAP_CENTER, DEFAULT_MAP_ZOOM)
        doc.map_widget = map_widget
    return doc.map_widget


def get_controls():
    doc = pn.state.curdoc
    if not hasattr(doc, "controls"):
        controls = build_downscaling_controls(
            get_models, CANE5_RUNS, SCENARIOS, PERIODS, get_state()
        )
        doc.controls = controls
    return doc.controls


def clear_controls():
    doc = pn.state.curdoc
    if hasattr(doc, "controls"):
        del doc.controls


def clear_map_widget():
    doc = pn.state.curdoc
    if hasattr(doc, "map_widget"):
        del doc.map_widget


def get_selected_climate_vars():
    controls = get_controls()
    selected = [
        controls[key].description
        for key in ["pr_toggle", "tasmax_toggle", "tasmin_toggle", "tasmean_toggle"]
        if controls[key].value
    ]

    tasmax_selected = controls["tasmax_toggle"].value
    tasmin_selected = controls["tasmin_toggle"].value
    if tasmax_selected and tasmin_selected:
        selected.append("multivar")

    return selected


def update_state_from_controls():
    state = get_state()
    controls = get_controls()
    state.region = controls["region"].value
    state.dataset = controls["dataset"].value
    state.technique = controls["technique"].value
    state.model = controls["model"].value
    state.canesm5_run = controls["canesm5_run"].value
    state.scenario = controls["scenario"].value
    state.period = controls["period"].value
    state.selected_variables = get_selected_climate_vars()


def make_overlay_layers(pt):
    marker = Marker(location=pt, interactive=False, draggable=False)
    lat_min_obs, lat_max_obs = pt[0] - 0.25, pt[0] + 0.25
    lon_min_obs, lon_max_obs = pt[1] - 0.25, pt[1] + 0.25
    lat_min_gcm, lat_max_gcm = pt[0] - 0.5, pt[0] + 0.5
    lon_min_gcm, lon_max_gcm = pt[1] - 0.5, pt[1] + 0.5

    gcm_layer = get_subdomain(
        lat_min_gcm,
        lat_max_gcm,
        lon_min_gcm,
        lon_max_gcm,
        "blue",
        "Medium-resolution inputs",
    )
    obs_layer = get_subdomain(
        lat_min_obs,
        lat_max_obs,
        lon_min_obs,
        lon_max_obs,
        "red",
        "High-resolution outputs",
    )

    bounds = {
        "lat_min_obs": lat_min_obs,
        "lat_max_obs": lat_max_obs,
        "lon_min_obs": lon_min_obs,
        "lon_max_obs": lon_max_obs,
        "lat_min_gcm": lat_min_gcm,
        "lat_max_gcm": lat_max_gcm,
        "lon_min_gcm": lon_min_gcm,
        "lon_max_gcm": lon_max_gcm,
    }
    return marker, gcm_layer, obs_layer, bounds


def step2_region_view():
    state = get_state()
    # Force create a fresh map widget to avoid reference conflicts
    map_widget = get_map_widget(force_new=True)
    controls = get_controls()
    control_box = controls["control_box_downscaling"]

    def handle_interact(**kwargs):
        pt = (round(kwargs["coordinates"][0], 5), round(kwargs["coordinates"][1], 5))
        controls["center_hover"].value = str(pt)
        if kwargs.get("type") != "click" or "coordinates" not in kwargs:
            return
        if not apply_location_rules(pt, controls, state):
            return

        marker, gcm_layer, obs_layer, bounds = make_overlay_layers(pt)
        if (
            hasattr(map_widget, "active_overlay")
            and map_widget.active_overlay in map_widget.layers
        ):
            map_widget.remove_layer(map_widget.active_overlay)
        overlay_group = LayerGroup(layers=(marker, gcm_layer, obs_layer))
        map_widget.add_layer(overlay_group)
        map_widget.active_overlay = overlay_group
        map_widget.center_point = pt
        controls["center"].value = str(pt)
        state.center_point = pt
        state.map_bounds = bounds

    # Attach the interaction handler to the fresh map widget
    map_widget.on_interaction(handle_interact)

    # Re-create overlay if there's a saved center point
    if state.center_point is not None:
        pt = state.center_point
        marker, gcm_layer, obs_layer, bounds = make_overlay_layers(pt)
        overlay_group = LayerGroup(layers=(marker, gcm_layer, obs_layer))
        map_widget.add_layer(overlay_group)
        map_widget.active_overlay = overlay_group
        map_widget.center_point = pt
        controls["center"].value = str(pt)

    doc = pn.state.curdoc
    if not getattr(doc, "dpad_wired", False):
        controls["shift_up_btn"].on_click(lambda e: shift_box(dy=0.5))
        controls["shift_down_btn"].on_click(lambda e: shift_box(dy=-0.5))
        controls["shift_left_btn"].on_click(lambda e: shift_box(dx=-0.5))
        controls["shift_right_btn"].on_click(lambda e: shift_box(dx=0.5))
        doc.dpad_wired = True

    continue_btn = build_panel_continue_button("Continue")
    back_btn = build_panel_continue_button("Back")

    def on_next(event):
        update_state_from_controls()
        missing = []
        if not state.center_point:
            missing.append("Map location")
        if not state.region.strip():
            missing.append("Study Area")
        if not state.selected_variables:
            missing.append("Climate Variable")
        if state.dataset == "CMIP6":
            for key in ["technique", "model", "scenario", "period"]:
                if not getattr(state, key):
                    missing.append(key.capitalize())
            if state.model == "CanESM5" and not state.canesm5_run:
                missing.append("CanESM5 Run")
        if missing:
            user_warn("⚠️ Please fill: " + ", ".join(missing), "warning")
            return
        next_step()

    def on_prev(event):
        prev_step()

    continue_btn.on_click(on_next)
    back_btn.on_click(on_prev)

    def handle_dataset_change(event):
        is_cmip6 = state.internal_dataset == "CMIP6"
        user_warn(f"Dataset changed to: {controls['dataset'].value}")
        if is_cmip6:
            for key in ["model", "canesm5_run", "technique", "scenario", "period"]:
                controls[key].disabled = False
            controls["technique"].value = "Univariate"
            state.technique = "Univariate"
            controls["model"].value = "ACCESS-CM2"
            state.model = "ACCESS-CM2"
            controls["scenario"].value = "ssp126"
            state.scenario = "ssp126"
            controls["period"].value = "1950-2010"
            state.period = "1950-2010"
            controls["canesm5_run"].value = "r1i1p2f1"
            state.canesm5_run = "r1i1p2f1"
        else:
            for key in ["model", "canesm5_run", "technique", "scenario", "period"]:
                controls[key].disabled = True

    def handle_model_change(event):
        is_canesm5 = controls["model"].value == "CanESM5"
        controls["canesm5_run"].disabled = not is_canesm5
        if is_canesm5:
            controls["canesm5_run"].value = "r1i1p2f1"
        else:
            controls["canesm5_run"].value = ""

    controls["dataset"].observe(handle_dataset_change, "value")
    controls["model"].observe(handle_model_change, "value")

    return pn.Column(
        pn.pane.Markdown("# Step 2: Select Region and Downscaling Parameters"),
        pn.Row(
            pn.panel(
                map_widget,
                sizing_mode="stretch_both",
                styles={
                    "position": "relative",
                    "z-index": "0",
                    "background": "rgba(255,255,255,0.65)",
                },
            ),
            sizing_mode="stretch_width",
        ),
        pn.panel(
            control_box,
            styles={
                "position": "absolute",
                "top": "10px",
                "right": "10px",
                "z-index": "10",
                "background": "rgba(255,255,255,0.65)",
                "padding": "10px",
                "border-radius": "8px",
                "box-shadow": "2px 2px 10px rgba(0,0,0,0.3)",
                "width": "300px",
            },
        ),
        pn.Row(get_user_warning_pane()),
        pn.Row(back_btn, continue_btn),
        width=1200,
        sizing_mode="fixed",
    )
