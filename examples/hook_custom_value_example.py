"""This example shows how to hook the property getting/setting process to
change the value before it is saved and before it is applied again.

E.g. consider that we have a property that stores a namedtuple that we need
to dump as a list (because yaml doesn't understand named tuple) and create
a named tuple again when restoring.

``get_config_property`` and
``apply_config_property`` are the needed hook methods, that are
automatically used if present in the class. See also ``apply_config_child``
for similarly hooking into applying the children objects.
The default, when not provided is to use ``apply_config``, so if
overriding, that should probably also be used for the base case.
"""
from collections import namedtuple
from tree_config import dump_config, load_config, apply_config, \
    read_config_from_object

Point = namedtuple('Point', ['x', 'y'])


class App:

    _config_props_ = ('point', 'name')

    point = Point(11, 34)

    name = ''

    def get_config_property(self, name):
        if name == 'point':
            return tuple(self.point)
        return getattr(self, name)

    def apply_config_property(self, name, value):
        if name == 'point':
            self.point = Point(*value)
        else:
            setattr(self, name, value)


if __name__ == '__main__':
    # create app and set properties
    app = App()

    # now get and save config to yaml file
    dump_config('custom_value_example.yaml', read_config_from_object(app))
    print(f'point is: {app.point}')

    # Now we should have a custom_value_example.yaml file with the contents:
    """
    name: ''
    point: [11, 34]
    """

    # load config and apply it
    apply_config(app, load_config(app, 'custom_value_example.yaml'))
    print(f'point is: {app.point}')

    # when run, this prints:
    """
    point is: Point(x=11, y=34)
    point is: Point(x=11, y=34)
    """
