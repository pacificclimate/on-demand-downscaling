import panel as pn
import os
from pathlib import Path
from time import time
from .widgets import AppState
from .config import (
    APP_NAME,
    MAGPIE_URL,
    CHICKADEE_URL,
    FINCH_URL,
    SERVICE_CHECK_TIMEOUT,
    SERVICE_STATUS_TTL_SECONDS,
)
import requests
import redis


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
        doc.header_pane = pn.Column(sizing_mode="stretch_width", margin=0)
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
    for attr in (
        "controls",
        "map_widget",
        "dpad_wired",
        "service_status_cache",
        "service_status_popup_visible",
    ):
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


def _check_queue_status():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    client = redis.from_url(redis_url)
    client.ping()
    return {"ok": True, "label": "Queue", "detail": "Redis queue reachable"}


def _check_wps_status(label, url):
    resp = requests.get(
        url,
        params={"service": "WPS", "request": "GetCapabilities", "version": "1.0.0"},
        timeout=SERVICE_CHECK_TIMEOUT,
    )
    resp.raise_for_status()
    if "Capabilities" not in resp.text and "capabilities" not in resp.text:
        raise ValueError("GetCapabilities response did not look valid.")
    return {"ok": True, "label": label, "detail": "WPS endpoint reachable"}


def get_service_status(force=False):
    doc = pn.state.curdoc
    now = time()
    cache = getattr(doc, "service_status_cache", None)
    if (
        not force
        and cache is not None
        and (now - cache["checked_at"]) < SERVICE_STATUS_TTL_SECONDS
    ):
        return cache["status"]

    checks = [
        ("queue", lambda: _check_queue_status()),
        ("chickadee", lambda: _check_wps_status("Chickadee", CHICKADEE_URL)),
        ("finch", lambda: _check_wps_status("Finch", FINCH_URL)),
    ]
    status = {}
    for key, check in checks:
        try:
            status[key] = check()
        except Exception as exc:
            label = key.capitalize() if key != "queue" else "Queue"
            status[key] = {"ok": False, "label": label, "detail": str(exc)}

    doc.service_status_cache = {"checked_at": now, "status": status}
    return status


def _service_status_summary(status):
    degraded = [item for item in status.values() if not item["ok"]]
    if not degraded:
        return "All required backend services are ready.", "success"

    lines = ["Required backend services are unavailable:"]
    for item in degraded:
        lines.append(f"- `{item['label']}`: {item['detail']}")
    return "\n".join(lines), "danger"


def toggle_service_status_popup():
    doc = pn.state.curdoc
    current = getattr(doc, "service_status_popup_visible", False)
    doc.service_status_popup_visible = not current
    update_header()


def update_service_status_popup():
    status = get_service_status()
    summary, level = _service_status_summary(status)
    return pn.pane.Alert(
        summary,
        alert_type=level,
        visible=True,
        sizing_mode="stretch_width",
    )


def update_header():
    header_pane = get_header_pane()
    header_pane.clear()
    doc = pn.state.curdoc
    state = get_state()

    title = pn.pane.HTML(
        f"<h2 style='margin:0'>{APP_NAME}</h2>",
        margin=(0, 10, 0, 0),
    )
    status_btn = pn.widgets.Button(
        name="Service Status",
        button_type="light",
        width=120,
    )
    status_btn.on_click(lambda event: toggle_service_status_popup())
    popup_visible = getattr(doc, "service_status_popup_visible", False)

    row_items = [title, pn.layout.HSpacer(), status_btn]
    if getattr(state, "authenticated", False):
        user_name = (
            getattr(state, "user", "") or getattr(state, "username", "") or "user"
        )
        welcome = pn.pane.Markdown(
            f"**Signed in as:** `{user_name}`",
            margin=(0, 10, 0, 0),
        )
        logout_btn = pn.widgets.Button(name="Logout", button_type="warning", width=100)
        logout_btn.on_click(lambda event: logout())
        row_items.extend([welcome, logout_btn])

    header_row = pn.Row(*row_items, sizing_mode="stretch_width", margin=0)
    header_pane.append(header_row)
    if popup_visible:
        header_pane.append(update_service_status_popup())


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
                    state.email = email
                    state.username = username
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
