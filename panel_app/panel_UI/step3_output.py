import panel as pn
from .state import get_state, next_step, prev_step
from .widgets import build_panel_radio_group, build_panel_continue_button
from .user_warnings import get_user_warning_pane


def step3_output_view():
    state = get_state()
    output_intent_options = {
        "Climate Indices Only (Recommended)": "indices",
        "High-resolution Outputs Only": "downscale",
        "High-resolution Outputs and Climate Indices": "both",
    }
    intent_selector = build_panel_radio_group(
        name="Select Desired Output",
        options=output_intent_options,
        state=state,
        attr="output_intent",
        button_type="default",
    )
    continue_btn = build_panel_continue_button("Continue")
    back_btn = build_panel_continue_button("Back")

    def on_next(event):
        state.output_intent = intent_selector.value
        next_step()

    def on_prev(event):
        prev_step()

    continue_btn.on_click(on_next)
    back_btn.on_click(on_prev)
    return pn.Column(
        pn.pane.Markdown("## Step 3: Desired Outputs"),
        intent_selector,
        pn.Row(back_btn, continue_btn),
        get_user_warning_pane(),
        width=1200,
        sizing_mode="fixed",
    )
