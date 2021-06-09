"""Basic example showing how to use tree_config.

We have a root class, App, that is configurable. The App class
additionally references two panel classes that is each configurable
as well.

Starting with the root App class, tree-config can dump all the properties to a
yaml file, and then load and restore the values to the properties.
"""
from pathlib import Path
from tree_config import dump_config, load_config, apply_config, \
    read_config_from_object


class App:

    _config_props_ = ('size', 'name')

    _config_children_ = {'app panel': 'panel1', 'home panel': 'panel2'}

    size = 12

    name = 'Desk'

    def __init__(self):
        self.panel1 = AppPanel()
        self.panel2 = HomePanel()


class AppPanel:

    _config_props_ = ('color', )

    color = 'A4FF67'


class HomePanel:

    _config_props_ = ('shape', )

    shape = 'circle'


if __name__ == '__main__':
    # file where yaml will be saved
    filename = Path('basic_example.yaml')

    # create app and set properties
    app = App()

    # now get and save config to yaml file
    dump_config(str(filename), read_config_from_object(app))
    print(f'Shape is: {app.panel2.shape}')

    # Now we should have a basic_example.yaml file with the following contents:
    """
    app panel: {color: A4FF67}
    home panel: {shape: circle}
    name: Desk
    size: 12
    """

    # change circle to square in the yaml file
    filename.write_text(filename.read_text().replace('circle', 'square'))

    # load config and apply it
    apply_config(app, load_config(app, str(filename)))
    print(f'Shape is: {app.panel2.shape}')

    # when run, this prints:
    """
    Shape is: circle
    Shape is: square
    """
