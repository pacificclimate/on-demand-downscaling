import panel as pn
from panel_helpers import create_map_ui

pn.extension("ipywidgets", "leaflet")

app = create_map_ui()
app.servable()
