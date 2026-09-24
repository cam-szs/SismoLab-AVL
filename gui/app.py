"""[BOILERPLATE - implemented] Main Tkinter window and notebook layout."""

import tkinter as tk
from tkinter import ttk


class SismoLabApp:
    """Build the main window and its functional view regions."""

    def __init__(self, root: tk.Tk | None = None) -> None:
        """Create the application window without starting the event loop."""
        self.root = root or tk.Tk()
        self.root.title("SismoLab AVL")
        self.root.geometry("1000x700")
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)
        for title in ("Trees", "Map", "Queue", "History / Audit", "Versions"):
            notebook.add(ttk.Frame(notebook), text=title)

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self.root.mainloop()
