import ipywidgets as widgets
from ipyleaflet import Map, LayerGroup, basemap_to_tiles, basemaps, Marker
import panel as pn
from inspect import getfullargspec
import param
from .config import BASE_SCENARIOS, SHOW_OBS_DOMAIN, SSP370

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
    precip_percentile = param.String(default="95 pct")
    precip_thresh = param.String(default="1 mm/day")
    tx_days_above_thresh = param.String(default="25 degC")
    tn_days_above_thresh = param.String(default="20 degC")
    tn_days_below_thresh = param.String(default="-10 degC")
    hdd_thresh = param.String(default="18 degC")
    cdd_thresh = param.String(default="18 degC")
    cold_spell_thresh = param.String(default="-15 degC")
    cold_spell_window = param.String(default="2 days")
    cwd_thresh = param.String(default="1 mm/day")
    cdd_dry_thresh = param.String(default="1 mm/day")
    heat_wave_tn_thresh = param.String(default="20 degC")
    heat_wave_tx_thresh = param.String(default="30 degC")
    heat_wave_window = param.String(default="2 days")
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
        "PCIC-Blend": "PCIC-Blend",
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


def build_scenario_buttons(
    state,
    attr="scenario",
    description="Scenario:",
    value=None,
    layout=None,
    disabled=False,
    **kwargs,
):
    if layout is None:
        layout = widgets.Layout(width="75%")

    rb = widgets.RadioButtons(
        options=list(BASE_SCENARIOS),
        description=description,
        value=value,
        layout=layout,
        disabled=disabled,
        **kwargs,
    )

    def _update(change):
        setattr(state, attr, change["new"])

    rb.observe(_update, names="value")

    def _refresh(*_):
        options = list(BASE_SCENARIOS)
        if state.internal_dataset == "CMIP6" and state.internal_technique == "MBCn":
            # Insert SSP3-7.0 before SSP5-8.5 (ssp585) so ordering is correct
            insert_at = next(
                (i for i, (_, v) in enumerate(options) if v == "ssp585"),
                len(options),
            )
            options.insert(insert_at, SSP370)

        rb.options = options
        desired = getattr(state, attr)
        valid = {v for _, v in options}

        if desired in valid:
            rb.value = desired
        else:
            rb.value = "ssp126" if "ssp126" in valid else next(iter(valid))
            setattr(state, attr, rb.value)

    state.param.watch(lambda e: _refresh(), attr)
    state.param.watch(lambda e: _refresh(), "dataset")
    state.param.watch(lambda e: _refresh(), "technique")

    _refresh()
    return rb


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
    # Hide readout textbox; a numeric editor is rendered beside the slider row.
    kwargs.setdefault("readout", False)
    kwargs.setdefault("tooltip", "")
    kwargs.setdefault("description_tooltip", "")
    valid_options = list(options)
    valid_values = set(valid_options)
    last_valid = {"value": value if value in valid_values else valid_options[0]}
    slider = widgets.SelectionSlider(
        options=options, value=value, description=description, **kwargs
    )

    def _update(change):
        new_value = change["new"]
        if new_value in valid_values:
            last_valid["value"] = new_value
            setattr(state, attr, new_value)
            return
        slider.value = last_valid["value"]

    slider.observe(_update, names="value")

    def _refresh(*a):
        current = getattr(state, attr)
        if current in valid_values:
            last_valid["value"] = current
            slider.value = current
        else:
            setattr(state, attr, last_valid["value"])
            slider.value = last_valid["value"]

    state.param.watch(lambda e: _refresh(), attr)
    return slider


# ----------- DYNAMIC INDEX STATE BUILDERS -----------


def build_index_checkbox(
    description, state, value=False, style=None, key_prefix=None, **kwargs
):
    if style is None:
        style = {"description_width": "initial"}
    key_base = (
        description.replace(" ", "_")
        .replace("-", "_")
        .replace(".", "")
        .replace(">", "gt")
        .replace("<", "lt")
    )
    key = f"{key_prefix}_{key_base}" if key_prefix else key_base
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
    get_models, CANE5_RUNS, PERIODS, state, description_style=None
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
        options=[("PCIC-Blend\n(1950-2012)", "PCIC-Blend"), "CanDCS"],
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
    scenario = build_scenario_buttons(
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
    PRECIP_PERCENTILE_OPTIONS,
    PRECIP_THRESHOLD_OPTIONS,
    TX_DAYS_ABOVE_THRESHOLD_OPTIONS,
    TN_DAYS_ABOVE_THRESHOLD_OPTIONS,
    TN_DAYS_BELOW_THRESHOLD_OPTIONS,
    HDD_THRESHOLD_OPTIONS,
    CDD_THRESHOLD_OPTIONS,
    COLD_SPELL_THRESHOLD_OPTIONS,
    COLD_SPELL_N_DAY_OPTIONS,
    CWD_THRESHOLD_OPTIONS,
    CDD_DRY_THRESHOLD_OPTIONS,
    HEAT_WAVE_TN_THRESHOLD_OPTIONS,
    HEAT_WAVE_TX_THRESHOLD_OPTIONS,
    HEAT_WAVE_N_DAY_OPTIONS,
    state,
):
    slider_layout = widgets.Layout(
        width="164px",
        min_width="164px",
        flex="0 0 164px",
        margin="0 6px 0 0",
    )
    slider_style = {"description_width": "72px"}
    rxnday = build_selection_slider(
        N_DAY_PRECIP_OPTIONS,
        state=state,
        attr="rxnday",
        value="1 day",
        description="N-day Precip:",
        layout=slider_layout,
        style=slider_style,
    )
    rnnmm = build_selection_slider(
        WETDAY_THRESHOLD_OPTIONS,
        state=state,
        attr="rnnmm",
        value="10 mm/day",
        description="PR:",
        layout=slider_layout,
        style=slider_style,
    )
    precip_percentile = build_selection_slider(
        PRECIP_PERCENTILE_OPTIONS,
        state=state,
        attr="precip_percentile",
        value="95 pct",
        description="Percentile:",
        layout=slider_layout,
        style=slider_style,
    )
    precip_thresh = build_selection_slider(
        PRECIP_THRESHOLD_OPTIONS,
        state=state,
        attr="precip_thresh",
        value="1 mm/day",
        description="PR:",
        layout=slider_layout,
        style=slider_style,
    )
    tx_days_above_thresh = build_selection_slider(
        TX_DAYS_ABOVE_THRESHOLD_OPTIONS,
        state=state,
        attr="tx_days_above_thresh",
        value="25 degC",
        description="TX:",
        layout=slider_layout,
        style=slider_style,
    )
    tn_days_above_thresh = build_selection_slider(
        TN_DAYS_ABOVE_THRESHOLD_OPTIONS,
        state=state,
        attr="tn_days_above_thresh",
        value="20 degC",
        description="TN:",
        layout=slider_layout,
        style=slider_style,
    )
    tn_days_below_thresh = build_selection_slider(
        TN_DAYS_BELOW_THRESHOLD_OPTIONS,
        state=state,
        attr="tn_days_below_thresh",
        value="-10 degC",
        description="TN:",
        layout=slider_layout,
        style=slider_style,
    )
    hdd_thresh = build_selection_slider(
        HDD_THRESHOLD_OPTIONS,
        state=state,
        attr="hdd_thresh",
        value="18 degC",
        description="TM:",
        layout=slider_layout,
        style=slider_style,
    )
    cdd_thresh = build_selection_slider(
        CDD_THRESHOLD_OPTIONS,
        state=state,
        attr="cdd_thresh",
        value="18 degC",
        description="TM:",
        layout=slider_layout,
        style=slider_style,
    )
    cold_spell_thresh = build_selection_slider(
        COLD_SPELL_THRESHOLD_OPTIONS,
        state=state,
        attr="cold_spell_thresh",
        value="-15 degC",
        description="TM:",
        layout=slider_layout,
        style=slider_style,
    )
    cold_spell_window = build_selection_slider(
        COLD_SPELL_N_DAY_OPTIONS,
        state=state,
        attr="cold_spell_window",
        value="2 days",
        description="N-days:",
        layout=slider_layout,
        style=slider_style,
    )
    cwd_thresh = build_selection_slider(
        CWD_THRESHOLD_OPTIONS,
        state=state,
        attr="cwd_thresh",
        value="1 mm/day",
        description="Wet:",
        layout=slider_layout,
        style=slider_style,
    )
    cdd_dry_thresh = build_selection_slider(
        CDD_DRY_THRESHOLD_OPTIONS,
        state=state,
        attr="cdd_dry_thresh",
        value="1 mm/day",
        description="Dry:",
        layout=slider_layout,
        style=slider_style,
    )
    heat_wave_tn_thresh = build_selection_slider(
        HEAT_WAVE_TN_THRESHOLD_OPTIONS,
        state=state,
        attr="heat_wave_tn_thresh",
        value="20 degC",
        description="TN:",
        layout=slider_layout,
        style=slider_style,
    )
    heat_wave_tx_thresh = build_selection_slider(
        HEAT_WAVE_TX_THRESHOLD_OPTIONS,
        state=state,
        attr="heat_wave_tx_thresh",
        value="30 degC",
        description="TX:",
        layout=slider_layout,
        style=slider_style,
    )
    heat_wave_window = build_selection_slider(
        HEAT_WAVE_N_DAY_OPTIONS,
        state=state,
        attr="heat_wave_window",
        value="2 days",
        description="N-days:",
        layout=slider_layout,
        style=slider_style,
    )
    return dict(
        rxnday=rxnday,
        rnnmm=rnnmm,
        precip_percentile=precip_percentile,
        precip_thresh=precip_thresh,
        tx_days_above_thresh=tx_days_above_thresh,
        tn_days_above_thresh=tn_days_above_thresh,
        tn_days_below_thresh=tn_days_below_thresh,
        hdd_thresh=hdd_thresh,
        cdd_thresh=cdd_thresh,
        cold_spell_thresh=cold_spell_thresh,
        cold_spell_window=cold_spell_window,
        cwd_thresh=cwd_thresh,
        cdd_dry_thresh=cdd_dry_thresh,
        heat_wave_tn_thresh=heat_wave_tn_thresh,
        heat_wave_tx_thresh=heat_wave_tx_thresh,
        heat_wave_window=heat_wave_window,
    )


def get_index_resolution_options(process, base_res, months, seasons):
    args = getfullargspec(process).args
    options = list(base_res) if "freq" in args else ["Annual"]
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
    sliders,
    MAX_SELECTED_INDICES,
    user_warn,
    state,
    all_index_checkboxes=None,
    description_style=None,
    key_prefix=None,
):
    if description_style is None:
        description_style = {"description_width": "initial"}
    if all_index_checkboxes is None:
        all_index_checkboxes = []

    def parse_numeric_option(option):
        if not isinstance(option, str):
            return None, None
        parts = option.split(" ", 1)
        try:
            number = int(parts[0])
        except ValueError:
            return None, None
        unit = parts[1] if len(parts) > 1 else ""
        return number, unit

    def clone_slider(template):
        return widgets.SelectionSlider(
            options=template.options,
            value=template.value,
            description=template.description,
            layout=template.layout,
            style=template.style,
            readout=template.readout,
            tooltip="",
            description_tooltip="",
            continuous_update=template.continuous_update,
            disabled=template.disabled,
            orientation=template.orientation,
        )

    threshold_specs = {
        "Max N-day Precip Amount": [{"slider": "rxnday", "param": "window"}],
        "Days with Precip over N-mm": [{"slider": "rnnmm", "param": "thresh"}],
        "Days Over Precip Percentile Threshold": [
            {"slider": "precip_percentile", "param": "percentile"},
            {"slider": "precip_thresh", "param": "thresh"},
        ],
        "Days Above a Specified TX": [
            {"slider": "tx_days_above_thresh", "param": "thresh"}
        ],
        "Days Above a Specified TN": [
            {"slider": "tn_days_above_thresh", "param": "thresh"}
        ],
        "Days Below a Specified TN": [
            {"slider": "tn_days_below_thresh", "param": "thresh"}
        ],
        "Heating Degree Days": [{"slider": "hdd_thresh", "param": "thresh"}],
        "Cooling Degree Days": [{"slider": "cdd_thresh", "param": "thresh"}],
        "Cold Spell Days": [
            {"slider": "cold_spell_thresh", "param": "thresh"},
            {"slider": "cold_spell_window", "param": "window"},
        ],
        "Maximum Length of Wet Spell": [{"slider": "cwd_thresh", "param": "thresh"}],
        "Maximum Length of Dry Spell": [
            {"slider": "cdd_dry_thresh", "param": "thresh"}
        ],
        "Heat Wave Number": [
            {"slider": "heat_wave_tn_thresh", "param": "tn_thresh"},
            {"slider": "heat_wave_tx_thresh", "param": "tx_thresh"},
            {"slider": "heat_wave_window", "param": "window"},
        ],
        "Heat Wave Days": [
            {"slider": "heat_wave_tx_thresh", "param": "tx_thresh"},
            {"slider": "heat_wave_window", "param": "window"},
        ],
        "Heat Wave Maximum Length": [
            {"slider": "heat_wave_tn_thresh", "param": "tn_thresh"},
            {"slider": "heat_wave_tx_thresh", "param": "tx_thresh"},
            {"slider": "heat_wave_window", "param": "window"},
        ],
    }
    checkboxes = []
    for index, process in indices.items():
        options = get_index_resolution_options(process, RESOLUTIONS, MONTHS, SEASONS)
        checkbox, key = build_index_checkbox(
            description=index,
            state=state,
            value=False,
            style=description_style,
            key_prefix=key_prefix,
            layout=widgets.Layout(width="256px", min_width="256px"),
        )
        dropdown = build_index_dropdown(
            options=options, state=state, value=options[0], key=key
        )
        dropdown.layout = widgets.Layout(width="110px", min_width="110px")
        if len(options) <= 1:
            dropdown.disabled = True
        children = [checkbox, dropdown]
        slider_templates = threshold_specs.get(index, [])
        row_sliders = [
            clone_slider(sliders[item["slider"]])
            for item in slider_templates
            if item["slider"] in sliders
        ]
        for slider, spec in zip(row_sliders, slider_templates):
            slider._is_threshold_control = True
            slider._threshold_param_key = spec["param"]
            numeric_map = {}
            unit = ""
            for raw in list(slider.options):
                option_value = raw[1] if isinstance(raw, tuple) else raw
                number, parsed_unit = parse_numeric_option(option_value)
                if number is None:
                    numeric_map = {}
                    break
                numeric_map[number] = option_value
                if not unit:
                    unit = parsed_unit

            if numeric_map:
                current_number, _ = parse_numeric_option(slider.value)
                numeric_input = widgets.BoundedIntText(
                    value=current_number,
                    min=min(numeric_map),
                    max=max(numeric_map),
                    step=1,
                    layout=widgets.Layout(width="46px", min_width="46px"),
                )
                unit_label = widgets.HTML(
                    value=f"<span>{unit}</span>",
                    layout=widgets.Layout(width="56px", min_width="56px"),
                )

                def _on_slider_change(change, num_input=numeric_input):
                    new_number, _ = parse_numeric_option(change["new"])
                    if new_number is not None and num_input.value != new_number:
                        num_input.value = new_number

                def _on_numeric_change(change, sl=slider, options_by_num=numeric_map):
                    number = int(change["new"])
                    target = options_by_num.get(number)
                    if target is None:
                        user_warn(
                            f"Invalid value for {sl.description}. Allowed values: {sorted(options_by_num)}",
                            "warning",
                        )
                        return
                    if sl.value != target:
                        sl.value = target

                slider.observe(_on_slider_change, names="value")
                numeric_input.observe(_on_numeric_change, names="value")
                children.append(
                    build_hbox(
                        [slider, numeric_input, unit_label],
                        layout=widgets.Layout(
                            align_items="center",
                            overflow="hidden",  # Removes horizontal scrollbar
                            flex="0 0 auto",
                            width="274px",
                            min_width="274px",
                            margin="0 1px 0 0",
                        ),
                    )
                )
            else:
                children.append(slider)
        all_index_checkboxes.append(checkbox)
        if key not in state.index_states or not isinstance(
            state.index_states[key], dict
        ):
            checkbox.value = False
            state.index_states[key] = {
                "selected": checkbox.value,
                "resolution": options[0] if options else None,
                "sliders": {
                    slider._threshold_param_key: slider.value for slider in row_sliders
                },
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

        for slider in row_sliders:

            def _update_slider(change, key=key):
                entry = state.index_states.get(key)
                if not isinstance(entry, dict):
                    entry = {}
                slider_values = entry.get("sliders", {})
                slider_key = getattr(change["owner"], "_threshold_param_key", None)
                if not slider_key:
                    return
                slider_values[slider_key] = change["new"]
                entry["sliders"] = slider_values
                state.index_states[key] = entry

            slider.observe(_update_slider, names="value")

        checkbox.observe(on_check, names="value")
        checkboxes.append(
            build_hbox(
                children,
                layout=widgets.Layout(
                    align_items="center",
                    justify_content="flex-start",
                    gap="1px",
                ),
            )
        )
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
        "## Step 4: Summary and Launch",
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
