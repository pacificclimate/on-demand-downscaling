import panel as pn
from .state import get_state, next_step, prev_step
from .widgets import (
    build_panel_continue_button,
    build_index_sliders,
    build_index_checkboxes,
    build_html,
    build_vbox,
)
from .user_warnings import user_warn, get_user_warning_pane
from .config import (
    N_DAY_PRECIP_OPTIONS,
    WETDAY_THRESHOLD_OPTIONS,
    SUMMER_DAY_THRESHOLD_OPTIONS,
    TROPICAL_NIGHTS_THRESHOLD_OPTIONS,
    INDEX_FUNCTIONS_STRUCTURE,
    RESOLUTIONS,
    MONTHS,
    SEASONS,
    MAX_SELECTED_INDICES,
)
from .config import finch


def step4_indices_view():
    state = get_state()
    if state.output_intent == "downscale":
        state.indices_selected = [] 
        return "SKIP"
    # Build sliders
    sliders = build_index_sliders(
        N_DAY_PRECIP_OPTIONS,
        WETDAY_THRESHOLD_OPTIONS,
        SUMMER_DAY_THRESHOLD_OPTIONS,
        TROPICAL_NIGHTS_THRESHOLD_OPTIONS,
        state,
    )
    rxnday = sliders["rxnday"]
    rnnmm = sliders["rnnmm"]
    summer_days = sliders["summer_days"]
    tropical_nights = sliders["tropical_nights"]
    # Build index functions for each variable
    index_functions = {}
    for var, funcs in INDEX_FUNCTIONS_STRUCTURE.items():
        index_functions[var] = {
            name: getattr(finch, func_name) for name, func_name in funcs
        }

    # Build index boxes
    index_boxes = {}
    all_index_checkboxes = []
    for var, funcs in index_functions.items():
        index_boxes[var], all_index_checkboxes = build_index_checkboxes(
            funcs,
            RESOLUTIONS,
            MONTHS,
            SEASONS,
            rxnday,
            rnnmm,
            summer_days,
            tropical_nights,
            MAX_SELECTED_INDICES,
            user_warn,
            state,
            all_index_checkboxes=all_index_checkboxes,
        )

    # Build vboxes
    pr_box = build_vbox(
        [build_html("<b>Precipitation Indices</b>")] + index_boxes["pr"]
    )
    tasmax_box = build_vbox(
        [build_html("<b>Max Temp Indices</b>")] + index_boxes["tasmax"]
    )
    tasmin_box = build_vbox(
        [build_html("<b>Min Temp Indices</b>")] + index_boxes["tasmin"]
    )
    tasmean_box = build_vbox(
        [build_html("<b>Mean Temp Indices</b>")] + index_boxes["tasmean"]
    )
    multivar_box = build_vbox(
        [build_html("<b>Multivariate Indices</b>")] + index_boxes["multivar"]
    )

    # Panel to hold visible index selectors
    indices_panel = pn.Column()

    def clear_hidden_checkboxes():
        """Clear checkboxes for variables that are no longer available"""
        available = set(state.selected_variables)
        for var, boxes in index_boxes.items():
            if var not in available:
                for box in boxes:
                    children = box.children
                    checkbox = children[0]
                    if checkbox.value:
                        checkbox.value = False

    def update_indices_panel():
        indices_panel.clear()
        available = set(state.selected_variables)
        user_warn(f"Updating indices panel with available: {available}")

        # Clear checkboxes for unavailable variables
        clear_hidden_checkboxes()

        state.indices_selected = [
            idx for idx in state.indices_selected if idx["variable"] in available
        ]

        # Hide all first
        for box in [pr_box, tasmax_box, tasmin_box, tasmean_box, multivar_box]:
            box.layout.display = "none"

        if "tasmax" in available:
            tasmax_box.layout.display = ""
            indices_panel.append(tasmax_box)
        if "tasmin" in available:
            tasmin_box.layout.display = ""
            indices_panel.append(tasmin_box)
        if "tasmean" in available:
            tasmean_box.layout.display = ""
            indices_panel.append(tasmean_box)
        if "pr" in available:
            pr_box.layout.display = ""
            indices_panel.append(pr_box)

        if "multivar" in available:
            multivar_box.layout.display = ""
            indices_panel.append(multivar_box)

    # In case step2 variables changed
    state.param.watch(lambda *events: update_indices_panel(), ["selected_variables"])
    update_indices_panel()

    continue_btn = build_panel_continue_button("Continue")
    back_btn = build_panel_continue_button("Back")

    def on_next(event):
        selected_indices = []
        available = set(state.selected_variables)

        for var, boxes in index_boxes.items():

            if var not in available:
                continue

            for box in boxes:
                if box.layout.display == "none":
                    continue

                # Each box: [Checkbox, Dropdown, (maybe Slider)]
                children = box.children
                checkbox = children[0]
                if checkbox.value:
                    entry = {
                        "variable": var,
                        "index_name": checkbox.description,
                    }
                    # Dropdown (resolution/month/season)
                    if len(children) > 1 and hasattr(children[1], "value"):
                        entry["resolution"] = children[1].value
                    # If a slider is present (N-day, N-mm, etc.)
                    if len(children) > 2 and hasattr(children[2], "value"):
                        entry["threshold"] = children[2].value
                    selected_indices.append(entry)

        state.indices_selected = selected_indices
        next_step()

    def on_prev(event):
        prev_step()

    continue_btn.on_click(on_next)
    back_btn.on_click(on_prev)

    return pn.Column(
        pn.pane.Markdown("## Step 4: Calculate Indices"),
        indices_panel,
        pn.Row(back_btn, continue_btn),
        get_user_warning_pane(),
        width=1200,
        sizing_mode="fixed",
    )
