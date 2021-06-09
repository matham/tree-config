"""In contrast to the basic example where we only used ``_config_props_``
and ``_config_children_``, we can hook the discovery of configuration properties
and configuration children that have their own properties.

``_config_props_`` and ``_config_children_`` are defined on a class, not on
instances. When ``tree-config`` uses them, it will walk the whole class
hierarchy and accumulate their values from all super classes because a
sub-class does not overwrite them, but rather adds to them.

Instead, if ``_config_props`` and/or ``_config_children`` is defined on a
class or instance, tree-config will use that value directly, instead of
walking ``_config_props_`` and/or ``_config_children_``, respectively.

Notice in the resultant yaml file how ``AppPanel`` contains the properties
of both ``RootPanel`` and ``AppPanel``, while ``HomePanel`` only has the
properties listed in ``_config_props``.
"""
from tree_config import dump_config, read_config_from_object


class App:

    _config_children_ = {'app panel': 'panel1', 'home panel': 'panel2'}

    def __init__(self):
        self.panel1 = AppPanel()
        self.panel2 = HomePanel()


class RootPanel:

    _config_props_ = ('size', 'name')

    size = 12

    name = 'Desk'


class AppPanel(RootPanel):

    _config_props_ = ('color', )

    color = 'A4FF67'


class HomePanel(AppPanel):

    _config_props_ = ('shape', )

    shape = 'circle'

    group = 'window'

    _config_props = ('group', 'size')


if __name__ == '__main__':
    # create app and set properties
    app = App()

    # now get and save config to yaml file
    dump_config('hook_properties.yaml', read_config_from_object(app))

    # Now we should have a hook_properties.yaml file with the contents:
    """
    app panel:
      color: A4FF67
      name: Desk
      size: 12
    home panel:
      group: window
      size: 12
    """
