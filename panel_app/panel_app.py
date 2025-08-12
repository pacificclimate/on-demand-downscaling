import panel as pn
from panel_UI.state import get_main_pane, help_pane, render

pn.extension("ipywidgets")

render()
pn.Column(get_main_pane(), pn.layout.HSpacer(), help_pane).servable()
