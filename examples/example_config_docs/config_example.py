"""Example used to extract doc strings into a rst file for the configurable
properties.

Do::

    echo $'Config\n===========' > source/config.rst
    make html
    make html

to see the rendered config docs. See the intro guide for more details.
"""


class App:
    """The app."""

    _config_props_ = ('size', 'name')

    _config_children_ = {'app panel': 'panel1', 'home panel': 'panel2'}

    size = 55
    """Some filename."""

    name = ''
    """Some name."""

    panel1: 'AppPanel' = None
    """The app panel."""

    panel2: 'HomePanel' = None
    """The home panel."""

    def __init__(self, size, name, color, shape):
        self.size = size
        self.name = name

        self.panel1 = AppPanel()
        self.panel1.color = color
        self.panel2 = HomePanel()
        self.panel2.shape = shape


class AppPanel:
    """The app panel."""

    _config_props_ = ('color', )

    color = ''
    """Color of the app."""


class HomePanel:
    """The home panel."""

    _config_props_ = ('shape', )

    shape = ''
    """Shape of the home."""
