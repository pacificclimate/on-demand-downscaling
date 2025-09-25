import ipywidgets as widgets
from ipyleaflet import Map, LayerGroup, basemap_to_tiles, basemaps, Marker
import panel as pn
from inspect import getfullargspec
import param
from .config import SHOW_OBS_DOMAIN

# ========== STATE ==========


class AppState(param.Parameterized):
    center_hover = param.String(default="")
    center = param.String(default="")
    region = param.String(default="")
    map_bounds = param.Dict(default={})
    pr = param.Boolean(default=True)
    tasmax = param.Boolean(default=False)
    tasmin = param.Boolean(default=False)
    tasmean = param.Boolean(default=False)
    dataset = param.Parameter(default=None)
    technique = param.Parameter(default=None)
    canesm5_run = param.Parameter(default=None)
    model = param.Parameter(default=None)
    scenario = param.Parameter(default=None)
    period = param.Parameter(default=None)
    output_intent = param.Parameter(default=None)
    rxnday = param.String(default="1 day")
    rnnmm = param.String(default="10 mm/day")
    summer_days = param.String(default="25 degC")
    tropical_nights = param.String(default="20 degC")
    index_states = param.Dict(default={})
    center_point = param.Parameter(default=None)
    selected_variables = param.List(default=[])
    indices_selected = param.List(default=[])
    email = param.String(default="")
    current_step = param.Integer(default=0)
    authenticated = param.Boolean(default=False)
    obs_domain = param.String(default="Canada Mosaic")

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


# ==========  WIDGET BUILDERS ==========


def build_toggle(description, state, attr, value=False, layout=None, **kwargs):
    if layout is None:
        layout = widgets.Layout(width="100px")
    toggle = widgets.ToggleButton(
        description=description, value=value, layout=layout, **kwargs
    )

    def _update(change):
        setattr(state, attr, change["new"])

    toggle.observe(_update, names="value")

    def _refresh(*a):
        toggle.value = getattr(state, attr)

    state.param.watch(lambda e: _refresh(), attr)
    return toggle


def build_dropdown(
    options, state, attr, description="", value=None, layout=None, **kwargs
):
    if layout is None:
        layout = widgets.Layout(width="200px")
    dropdown = widgets.Dropdown(
        options=options, description=description, value=value, layout=layout, **kwargs
    )

    def _update(change):
        setattr(state, attr, change["new"])

    dropdown.observe(_update, names="value")

    def _refresh(*a):
        dropdown.value = getattr(state, attr)

    state.param.watch(lambda e: _refresh(), attr)
    return dropdown


def build_text(
    description,
    state,
    attr,
    placeholder="",
    value=None,
    layout=None,
    style=None,
    **kwargs,
):
    if layout is None:
        layout = widgets.Layout(width="210px")
    if style is None:
        style = {"description_width": "initial"}
    text = widgets.Text(
        description=description,
        placeholder=placeholder,
        value=value,
        layout=layout,
        style=style,
        **kwargs,
    )

    def _update(change):
        setattr(state, attr, change["new"])

    text.observe(_update, names="value")

    def _refresh(*a):
        text.value = getattr(state, attr)

    state.param.watch(lambda e: _refresh(), attr)
    return text


def build_radio_buttons(
    options,
    state,
    attr,
    description="",
    value=None,
    layout=None,
    disabled=False,
    **kwargs,
):
    if layout is None:
        layout = widgets.Layout(width="75%")
    rb = widgets.RadioButtons(
        options=options,
        description=description,
        value=value,
        layout=layout,
        disabled=disabled,
        **kwargs,
    )

    def _update(change):
        setattr(state, attr, change["new"])

    rb.observe(_update, names="value")

    def _refresh(*a):
        rb.value = getattr(state, attr)

    state.param.watch(lambda e: _refresh(), attr)
    return rb


def build_button(description="Button", button_style="", **kwargs):
    return widgets.Button(description=description, button_style=button_style, **kwargs)


def build_selection_slider(options, state, attr, value=None, description="", **kwargs):
    if value is None and options:
        value = options[0]
    slider = widgets.SelectionSlider(
        options=options, value=value, description=description, **kwargs
    )

    def _update(change):
        setattr(state, attr, change["new"])

    slider.observe(_update, names="value")

    def _refresh(*a):
        slider.value = getattr(state, attr)

    state.param.watch(lambda e: _refresh(), attr)
    return slider


# ----------- DYNAMIC INDEX STATE BUILDERS -----------


def build_index_checkbox(description, state, value=False, style=None, **kwargs):
    if style is None:
        style = {"description_width": "initial"}
    key = (
        description.replace(" ", "_")
        .replace("-", "_")
        .replace(".", "")
        .replace(">", "gt")
        .replace("<", "lt")
    )
    if key not in state.index_states or not isinstance(state.index_states[key], dict):
        state.index_states[key] = {
            "selected": value,
            "resolution": None,
            "slider": None,
        }

    cb = widgets.Checkbox(
        description=description,
        value=state.index_states.get(key, {}).get("selected", value),
        style=style,
        **kwargs,
    )

    def _update(change):
        entry = state.index_states.get(key)
        if not isinstance(entry, dict):
            entry = {"selected": False, "resolution": None, "slider": None}
        entry["selected"] = change["new"]
        state.index_states[key] = entry

    cb.observe(_update, names="value")

    def _refresh(*a):
        cb.value = state.index_states.get(key, {}).get("selected", False)

    state.param.watch(lambda e: _refresh(), "index_states")
    return cb, key


def build_index_dropdown(options, state, key, value="Annual", description="", **kwargs):
    default_value = value if value is not None else (options[0] if options else None)
    if key not in state.index_states or not isinstance(state.index_states[key], dict):
        state.index_states[key] = {
            "selected": False,
            "resolution": default_value,
            "slider": None,
        }
    if state.index_states[key].get("resolution") is None:
        state.index_states[key]["resolution"] = default_value
    dropdown = widgets.Dropdown(
        options=options,
        description=description,
        value=state.index_states[key]["resolution"],
        **kwargs,
    )

    def _update(change):
        entry = state.index_states.get(key)
        if not isinstance(entry, dict):
            entry = {
                "selected": False,
                "resolution": options[0] if options else None,
                "slider": None,
            }
        entry["resolution"] = change["new"]
        state.index_states[key] = entry

    dropdown.observe(_update, names="value")

    def _refresh(*a):
        dropdown.value = state.index_states[key].get(
            "resolution", options[0] if options else None
        )

    state.param.watch(lambda e: _refresh(), "index_states")
    return dropdown


# ---------------------------------------------------------------


def build_html(html_string):
    return widgets.HTML(html_string)


def build_hbox(children, layout=None):
    if layout is None:
        return widgets.HBox(children=children)
    return widgets.HBox(children=children, layout=layout)


def build_vbox(children, layout=None):
    if layout is None:
        return widgets.VBox(children=children)
    return widgets.VBox(children=children, layout=layout)


def build_box(children, layout=None):
    if layout is None:
        return widgets.Box(children=children)
    return widgets.Box(children=children, layout=layout)


# ---- PANEL BUILDERS ----


def build_panel_radio_group(name, options, state, attr, button_type="primary"):
    widget = pn.widgets.RadioButtonGroup(
        name=name, options=options, button_type=button_type
    )
    widget.link(state, value=attr)
    return widget


def build_panel_continue_button(label="Continue"):
    return pn.widgets.Button(name=label, button_type="primary")


# ========== FACTORIES USING BUILDERS ==========


def build_map(default_center, default_zoom):
    mapnik = basemap_to_tiles(basemaps.OpenStreetMap.Mapnik)
    mapnik.base = True
    m = Map(
        basemap=mapnik,
        center=default_center,
        zoom=default_zoom,
        layout=widgets.Layout(height="600px"),
    )
    return m


def legend_html():
    return build_html(
        """
        <div>
        <b>Subdomains</b><br>
        <span style="color: blue;">&#9632;</span> Medium-resolution inputs<br>
        <span style="color: red;">&#9632;</span> High-resolution outputs
        </div>
    """
    )


def build_downscaling_controls(
    get_models, CANE5_RUNS, SCENARIOS, PERIODS, state, description_style=None
):
    if description_style is None:
        description_style = {"description_width": "initial"}
    center_hover = build_text(
        description="",
        style=description_style,
        placeholder="Coordinates",
        state=state,
        attr="center_hover",
    )
    center = build_text(
        description="Center:",
        style=description_style,
        state=state,
        attr="center",
    )

    shift_up_btn = build_button("⬆️ Up", layout=widgets.Layout(width="80px"))
    shift_down_btn = build_button("⬇️ Down", layout=widgets.Layout(width="80px"))
    shift_left_btn = build_button("⬅️ Left", layout=widgets.Layout(width="80px"))
    shift_right_btn = build_button("➡️ Right", layout=widgets.Layout(width="80px"))
    pad_row_style = widgets.Layout(justify_content="center", width="92%")
    dpad_label = build_html("<b>Shift center:</b>")
    dpad = build_vbox(
        [
            dpad_label,
            build_hbox([shift_up_btn], layout=pad_row_style),
            build_hbox(
                [shift_left_btn, shift_down_btn, shift_right_btn], layout=pad_row_style
            ),
        ],
    )
    region = build_text(
        description="Study Area:",
        placeholder="e.g. Thompson River",
        style=description_style,
        state=state,
        attr="region",
    )
    pr_toggle = build_toggle("pr", state=state, attr="pr", value=True)
    tasmax_toggle = build_toggle("tasmax", state=state, attr="tasmax")
    tasmin_toggle = build_toggle("tasmin", state=state, attr="tasmin")
    tasmean_toggle = build_toggle("tasmean", state=state, attr="tasmean")
    clim_vars_label = build_html("<b>Variables:</b>")
    clim_vars = build_vbox(
        [clim_vars_label, pr_toggle, tasmax_toggle, tasmin_toggle, tasmean_toggle],
    )
    obs_domain = None
    if SHOW_OBS_DOMAIN:
        obs_domain = build_radio_buttons(
            options=["Canada Mosaic", "BC PRISM"],
            description="Obs domain:",
            value=state.obs_domain,  # default in AppState
            state=state,
            attr="obs_domain",
            layout=widgets.Layout(width="100%"),
        )
        legend_and_toggle = build_vbox([legend_html(), obs_domain])
        legend_row = build_hbox(
            [clim_vars, legend_and_toggle], layout=widgets.Layout(width="75%")
        )
    else:
        legend_row = build_hbox(
            [clim_vars, legend_html()], layout=widgets.Layout(width="75%")
        )

    dataset = build_radio_buttons(
        options=["PCIC-Blend", "CanDCS"],
        description="Dataset:",
        value="PCIC-Blend",
        state=state,
        attr="dataset",
    )
    technique = build_radio_buttons(
        options=["Univariate", "Multivariate"],
        description="Technique:",
        disabled=True,
        value="Univariate",
        state=state,
        attr="technique",
    )
    canesm5_run = build_dropdown(
        options=[""] + CANE5_RUNS,
        description="CanESM5 run:",
        disabled=True,
        value="",
        state=state,
        attr="canesm5_run",
    )
    model = build_dropdown(
        options=[""] + get_models(),
        description="Model:",
        disabled=True,
        state=state,
        attr="model",
    )
    scenario = build_radio_buttons(
        options=SCENARIOS,
        description="Scenario:",
        disabled=True,
        state=state,
        attr="scenario",
    )
    period = build_radio_buttons(
        options=PERIODS,
        description="Period:",
        disabled=True,
        state=state,
        attr="period",
    )
    box_layout = widgets.Layout(
        display="flex", flex_flow="column", width="120%", align_items="center"
    )
    control_box_downscaling = build_box(
        [
            center_hover,
            center,
            region,
            dpad,
            legend_row,
            build_hbox([dataset, technique], layout=widgets.Layout(width="75%")),
            model,
            canesm5_run,
            build_hbox([scenario, period], layout=widgets.Layout(width="75%")),
        ],
        layout=box_layout,
    )
    return dict(
        center_hover=center_hover,
        center=center,
        region=region,
        pr_toggle=pr_toggle,
        tasmax_toggle=tasmax_toggle,
        tasmin_toggle=tasmin_toggle,
        tasmean_toggle=tasmean_toggle,
        clim_vars=clim_vars,
        **({"obs_domain": obs_domain} if obs_domain is not None else {}),
        dataset=dataset,
        technique=technique,
        canesm5_run=canesm5_run,
        model=model,
        scenario=scenario,
        period=period,
        control_box_downscaling=control_box_downscaling,
        shift_up_btn=shift_up_btn,
        shift_down_btn=shift_down_btn,
        shift_left_btn=shift_left_btn,
        shift_right_btn=shift_right_btn,
    )


def build_index_sliders(
    N_DAY_PRECIP_OPTIONS,
    WETDAY_THRESHOLD_OPTIONS,
    SUMMER_DAY_THRESHOLD_OPTIONS,
    TROPICAL_NIGHTS_THRESHOLD_OPTIONS,
    state,
):
    rxnday = build_selection_slider(
        N_DAY_PRECIP_OPTIONS,
        state=state,
        attr="rxnday",
        value="1 day",
        description="N-day Precip:",
    )
    rnnmm = build_selection_slider(
        WETDAY_THRESHOLD_OPTIONS,
        state=state,
        attr="rnnmm",
        value="10 mm/day",
        description="Wetday Threshold:",
    )
    summer_days = build_selection_slider(
        SUMMER_DAY_THRESHOLD_OPTIONS,
        state=state,
        attr="summer_days",
        value="25 degC",
        description="Summer Day Threshold:",
    )
    tropical_nights = build_selection_slider(
        TROPICAL_NIGHTS_THRESHOLD_OPTIONS,
        state=state,
        attr="tropical_nights",
        value="20 degC",
        description="Tropical Nights Threshold:",
    )
    return dict(
        rxnday=rxnday,
        rnnmm=rnnmm,
        summer_days=summer_days,
        tropical_nights=tropical_nights,
    )


def get_index_resolution_options(process, base_res, months, seasons):
    options = list(base_res)
    args = getfullargspec(process).args
    if "month" in args:
        options += months
    if "season" in args:
        options += seasons
    return options


def build_index_checkboxes(
    indices,
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
    all_index_checkboxes=None,
    description_style=None,
):
    if description_style is None:
        description_style = {"description_width": "initial"}
    if all_index_checkboxes is None:
        all_index_checkboxes = []

    slider_map = {
        "Max N-day Precip Amount": rxnday,
        "Days with Precip over N-mm": rnnmm,
        "Summer Days": summer_days,
        "Tropical Nights": tropical_nights,
    }
    checkboxes = []
    for index, process in indices.items():
        options = get_index_resolution_options(process, RESOLUTIONS, MONTHS, SEASONS)
        checkbox, key = build_index_checkbox(
            description=index, state=state, value=False, style=description_style
        )
        dropdown = build_index_dropdown(
            options=options, state=state, value=options[0], key=key
        )
        children = [checkbox, dropdown]
        slider = slider_map.get(index)
        if slider:
            children.append(slider)
        all_index_checkboxes.append(checkbox)
        if key not in state.index_states or not isinstance(
            state.index_states[key], dict
        ):
            checkbox.value = False
            state.index_states[key] = {
                "selected": checkbox.value,
                "resolution": options[0] if options else None,
                "slider": slider.value if slider else None,
            }

        def on_check(event, cb=checkbox):
            if sum(cb_.value for cb_ in all_index_checkboxes) > MAX_SELECTED_INDICES:
                cb.value = False
                user_warn(
                    f"You can select a maximum of {MAX_SELECTED_INDICES} indices."
                )
                print(f"You can select a maximum of {MAX_SELECTED_INDICES} indices.")

        def _update_check(change, key=key):
            entry = state.index_states.get(key, {})
            if not isinstance(entry, dict):
                entry = {"selected": False, "resolution": RESOLUTIONS[0]}
            entry["selected"] = change["new"]
            state.index_states[key] = entry

        checkbox.observe(_update_check, names="value")

        def _update_dropdown(change, key=key):
            entry = state.index_states.get(key)
            if not isinstance(entry, dict):
                entry = {}
            entry["resolution"] = change["new"]
            state.index_states[key] = entry

        dropdown.observe(_update_dropdown, names="value")

        if slider:

            def _update_slider(change, key=key):
                entry = state.index_states.get(key)
                if not isinstance(entry, dict):
                    entry = {}
                entry["slider"] = change["new"]
                state.index_states[key] = entry

            slider.observe(_update_slider, names="value")

        checkbox.observe(on_check, names="value")
        checkboxes.append(build_hbox(children))
    return checkboxes, all_index_checkboxes


def summary_markdown(state):
    center = getattr(state, "center", "-")
    dataset = getattr(state, "dataset", "-")
    internal_dataset = getattr(state, "internal_dataset", "-")
    is_cmip6 = internal_dataset == "CMIP6"
    model = getattr(state, "model", "-")
    is_canesm5 = model == "CanESM5"
    scenario = getattr(state, "scenario", "-") if is_cmip6 else "-"
    period = getattr(state, "period", "-") if is_cmip6 else "-"
    technique = getattr(state, "technique", "-") if is_cmip6 else "-"
    internal_technique = getattr(state, "internal_technique", "-") if is_cmip6 else "-"
    canesm5_run = getattr(state, "canesm5_run", "-") if is_cmip6 and is_canesm5 else "-"
    region = getattr(state, "region", "-")
    variables = (
        ", ".join(getattr(state, "selected_variables", []))
        if hasattr(state, "selected_variables") and state.selected_variables
        else "-"
    )
    intent = getattr(state, "output_intent", "-")
    includes_downscaling = "✓" if intent != "indices" else "✗"

    lines = [
        "## Summary",
        f"**Center**: {center}",
        f"**Region**: {region}",
        f"**Dataset**: {dataset} ({internal_dataset})",
    ]
    if is_cmip6:
        lines.append(f"**Technique**: {technique} ({internal_technique})")
        lines.append(f"**Model**: {model}")
        if is_canesm5:
            lines.append(f"**CanESM5 Run**: {canesm5_run}")
        lines.append(f"**Scenario**: {scenario}")
        lines.append(f"**Period**: {period}")
    lines += [
        f"**Variables**: {variables}",
        f"**Intent**: {intent}",
        f"Includes downscaling output: {includes_downscaling}",
    ]

    if hasattr(state, "indices_selected") and state.indices_selected:
        lines.append("**Selected Indices:**")
        for idx in state.indices_selected:
            desc = idx.get("index_name", "-").replace("_", " ")
            res = idx.get("resolution", "-")
            thresh = idx.get("threshold", None)
            thresh_str = f", N={thresh}" if thresh is not None else ""
            var = idx.get("variable", "-")
            lines.append(f"- **{desc}** ({var}, {res}{thresh_str})")

    return "\n".join(lines)
