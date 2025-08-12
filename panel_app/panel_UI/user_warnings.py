import panel as pn

def get_user_warning_pane():
    doc = pn.state.curdoc
    if not hasattr(doc, "user_warning_pane"):
        doc.user_warning_pane = pn.pane.Alert(
            "", alert_type="info", visible=False, sizing_mode="stretch_width"
        )
    return doc.user_warning_pane

def get_user_warnings_log():
    doc = pn.state.curdoc
    if not hasattr(doc, "user_warnings_log"):
        doc.user_warnings_log = []
    return doc.user_warnings_log

def user_warn(message, level="light"):
    """
    Display a user-facing warning or message in the alert pane.
    Level: 'info', 'success', 'warning', 'danger'
    """
    log = get_user_warnings_log()
    pane = get_user_warning_pane()
    log.append((level, message))
    latest = log[-3:]
    pane.alert_type = latest[-1][0]
    pane.object = "<br>".join(f"[{lvl.upper()}] {msg}" for lvl, msg in latest)
    pane.markdown = False
    pane.visible = True
