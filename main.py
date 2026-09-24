"""[BOILERPLATE - implemented] Application entry point."""

from sismolab_avl.gui.app import SismoLabApp


def main() -> None:
    """Create the desktop application and start its Tkinter event loop."""
    SismoLabApp().run()


if __name__ == "__main__":
    main()
