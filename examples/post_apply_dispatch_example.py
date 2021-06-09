"""After applying configuration to a object and its children objects,
tree-config will call the ``post_config_applied`` method of the object, if
the method exists.
"""
from tree_config import dump_config, load_config, apply_config, \
    read_config_from_object


class App:

    _config_props_ = ('size', 'name')

    _config_children_ = {'app panel': 'panel'}

    size = 12

    name = 'Desk'

    def __init__(self):
        self.panel = Panel()

    def apply_config_property(self, name, value):
        print('applying', name)
        setattr(self, name, value)

    def post_config_applied(self):
        print('done applying app')


class Panel:

    _config_props_ = ('color', )

    color = 'A4FF67'

    def apply_config_property(self, name, value):
        print('applying', name)
        setattr(self, name, value)

    def post_config_applied(self):
        print('done applying panel')


if __name__ == '__main__':
    # create app and set properties
    app = App()

    # now get and save config to yaml file
    dump_config('post_apply_dispatch.yaml', read_config_from_object(app))
    # load config and apply it
    apply_config(app, load_config(app, 'post_apply_dispatch.yaml'))

    # when run, this prints:
    """
    applying color
    done applying panel
    applying name
    applying size
    done applying app
    """
