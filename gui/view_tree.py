"""[STUB - team must implement] AVL and BST Matplotlib view."""

from matplotlib.figure import Figure


class TreeView:
    """Render AVL/BST structures without deciding their academic rules."""

    def __init__(self) -> None:
        """Create the Matplotlib figure used by the tree view."""
        self.figure = Figure(figsize=(8, 5))

    def draw(self, tree: object) -> None:
        """Draw a tree supplied by the domain layer."""
        raise NotImplementedError("TODO: implement AVL/BST tree visualization")
