import panel as pn
from pathlib import Path
from .widgets import AppState
from .config import MAGPIE_URL
import requests


def get_state() -> AppState:
    doc = pn.state.curdoc
    if not hasattr(doc, "app_state"):
        doc.app_state = AppState()
    return doc.app_state


def get_main_pane():
    doc = pn.state.curdoc
    if not hasattr(doc, "main_pane"):
        doc.main_pane = pn.Column()
    return doc.main_pane


def get_help_pane():
    doc = pn.state.curdoc
    if not hasattr(doc, "help_pane"):
        doc.help_pane = pn.pane.Markdown("", width=600, min_height=100)
    return doc.help_pane


def update_help(step):
    file = STEP_README_FILES.get(step)
    help_pane = get_help_pane()
    if file and file.exists():
        help_pane.object = file.read_text()
    else:
        help_pane.object = "*No help available for this step.*"


STEP_README_FILES = {
    0: Path(__file__).parent / "help_docs/STEP1.md",
    1: Path(__file__).parent / "help_docs/STEP2.md",
    2: Path(__file__).parent / "help_docs/STEP3.md",
    3: Path(__file__).parent / "help_docs/STEP4.md",
    4: Path(__file__).parent / "help_docs/STEP5.md",
}


def render():
    state = get_state()
    main_pane = get_main_pane()
    main_pane.clear()

    from .step1_email import step1_authentication
    from .step2_downscale import step2_region_view
    from .step3_output import step3_output_view
    from .step4_indices import step4_indices_view
    from .step5_summary import step5_summary_view

    step = getattr(state, "current_step", 0)

    if getattr(state, "authenticated", False):
        if step == 0:
            main_pane.append(step1_authentication(next_step))
        elif step == 1:
            main_pane.append(step2_region_view())
        elif step == 2:
            main_pane.append(step3_output_view())
        elif step == 3:
            view = step4_indices_view()
            if view == "SKIP":
                state.current_step += 1
                render()
                return
            main_pane.append(view)
        elif step == 4:
            main_pane.append(step5_summary_view())
        else:
            main_pane.append(pn.pane.Markdown("All steps complete."))
    else:
        # Try auto-login with cookie (set per user)
        try:
            auth_cookie = pn.state.cookies.get("auth_tkt")
            if auth_cookie:
                r = requests.get(
                    f"{MAGPIE_URL}/session",
                    cookies={"auth_tkt": auth_cookie},
                    timeout=3,
                )
                if r.status_code == 200 and r.json().get("authenticated"):
                    username = r.json().get("user", {}).get("user_name", "user")
                    email = r.json().get("user", {}).get("email", "user")
                    state.authenticated = True
                    state.email = email
                    state.username = username
                    render()  # rerun with new state
                    return
        except Exception:
            pass
        main_pane.append(step1_authentication(next_step))

    # Show help for current step
    update_help(step)


def next_step(event=None):
    state = get_state()
    state.current_step += 1
    render()


def prev_step(event=None):
    state = get_state()
    if state.current_step > 0:
        state.current_step -= 1
        render()


def set_step(step_number):
    state = get_state()
    if 0 <= step_number <= 4:
        state.current_step = step_number
        render()
    else:
        raise ValueError(
            f"Invalid step number: {step_number}. Must be between 0 and 4."
        )
