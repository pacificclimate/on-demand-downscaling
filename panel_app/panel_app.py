import panel as pn
from panel_UI.config import APP_NAME
from panel_UI.state import get_header_pane, get_main_pane, get_help_pane, render

pn.extension("ipywidgets")

render()
pn.Column(get_header_pane(), get_main_pane(), pn.layout.HSpacer(), get_help_pane()).servable(
    title=APP_NAME
)
