"""[STUB - team must implement] Geographic event and station view."""

from matplotlib.figure import Figure


class MapView:
    """Render stations, zones, and seismic events on a geographic plane."""

    def __init__(self) -> None:
        """Create the Matplotlib figure used by the map view."""
        self.figure = Figure(figsize=(8, 5))

    def draw(self, data: object) -> None:
        """Draw geographic data using the selected plotting policy."""
        raise NotImplementedError("TODO: implement geographic map visualization")
