import panel as pn
from pathlib import Path
from .widgets import AppState
from .config import APP_NAME, MAGPIE_URL
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


def get_header_pane():
    doc = pn.state.curdoc
    if not hasattr(doc, "header_pane"):
        doc.header_pane = pn.Row(sizing_mode="stretch_width")
    return doc.header_pane


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
    0: Path(__file__).parent / "help_docs/STEP0.md",
    1: Path(__file__).parent / "help_docs/STEP1.md",
    2: Path(__file__).parent / "help_docs/STEP2.md",
    3: Path(__file__).parent / "help_docs/STEP3.md",
    4: Path(__file__).parent / "help_docs/STEP4.md",
}


def reset_ui_cache():
    doc = pn.state.curdoc
    for attr in ("controls", "map_widget", "dpad_wired"):
        if hasattr(doc, attr):
            delattr(doc, attr)
    if hasattr(doc, "user_warnings_log"):
        doc.user_warnings_log = []
    if hasattr(doc, "user_warning_pane"):
        doc.user_warning_pane.object = ""
        doc.user_warning_pane.visible = False


def reset_app_state():
    doc = pn.state.curdoc
    reset_ui_cache()
    doc.app_state = AppState()
    return doc.app_state


def logout():
    auth_cookie = pn.state.cookies.get("auth_tkt")
    try:
        if auth_cookie:
            requests.get(
                f"{MAGPIE_URL}/signout",
                cookies={"auth_tkt": auth_cookie},
                timeout=3,
                allow_redirects=False,
            )
    except Exception:
        pass

    try:
        pn.state.cookies.pop("auth_tkt", None)
    except Exception:
        try:
            pn.state.cookies.update({"auth_tkt": ""})
        except Exception:
            pass

    state = reset_app_state()
    state.current_step = 0
    state.authenticated = False
    render()


def update_header():
    header_pane = get_header_pane()
    header_pane.clear()
    state = get_state()

    title = pn.pane.Markdown(
        f"## {APP_NAME}",
        margin=(0, 10, 0, 0),
    )

    if not getattr(state, "authenticated", False):
        header_pane.append(title)
        return

    user_name = getattr(state, "user", "") or getattr(state, "username", "") or "user"
    welcome = pn.pane.Markdown(
        f"**Signed in as:** `{user_name}`",
        margin=(0, 10, 0, 0),
    )
    logout_btn = pn.widgets.Button(name="Logout", button_type="warning", width=100)
    logout_btn.on_click(lambda event: logout())
    header_pane.extend([title, pn.layout.HSpacer(), welcome, logout_btn])


def render():
    state = get_state()
    main_pane = get_main_pane()
    main_pane.clear()

    from .step0_email import step0_authentication
    from .step1_downscale import step1_region_view
    from .step2_output import step2_output_view
    from .step3_indices import step3_indices_view
    from .step4_summary import step4_summary_view

    step = getattr(state, "current_step", 0)

    if getattr(state, "authenticated", False):
        if step == 0:
            main_pane.append(step0_authentication(next_step))
        elif step == 1:
            main_pane.append(step1_region_view())
        elif step == 2:
            main_pane.append(step2_output_view())
        elif step == 3:
            view = step3_indices_view()
            if view == "SKIP":
                state.current_step += 1
                render()
                return
            main_pane.append(view)
        elif step == 4:
            main_pane.append(step4_summary_view())
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
                    state.user = username
                    state.username = username
                    state.email = email
                    render()  # rerun with new state
                    return
        except Exception:
            pass
        main_pane.append(step0_authentication(next_step))

    # Show help for current step
    update_help(step)
    update_header()


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
