"""This example shows how to hook yaml so it can save and restore
custom data types. We will use a custom yaml tag to represent the object.

E.g. consider that we have a property that stores a namedtuple that we need
to dump as a list (because yaml doesn't understand named tuple) and create
a named tuple again when restoring.

See also ``yaml_dumps`` and ``yaml_loads`` for additional customization.
Most functions take a ``yaml_dump_str`` / ``yaml_load_str``to allow
customizing the yaml objects. See also ``register_torch_yaml_support``
in ``tree_config.yaml`` for a more complete example as well as some built-in
optional representers.
"""
from collections import namedtuple
from tree_config import dump_config, load_config, apply_config, \
    read_config_from_object
from ruamel.yaml import BaseConstructor, BaseRepresenter

Point = namedtuple('Point', ['x', 'y'])

yaml_tag = '!tree_config_example_point'


def _represent_point(representer: BaseRepresenter, val):
    return representer.represent_sequence(yaml_tag, tuple(val))


def _construct_point(constructor: BaseConstructor, tag, node):
    return Point(*constructor.construct_sequence(node))


def register_point_yaml_support() -> None:
    BaseRepresenter.add_multi_representer(Point, _represent_point)
    BaseConstructor.add_multi_constructor(yaml_tag, _construct_point)


class App:

    _config_props_ = ('point', 'name')

    point = Point(11, 34)

    name = ''


if __name__ == '__main__':
    # register the yaml constructor / representer
    register_point_yaml_support()
    # create app and set properties
    app = App()

    # now get and save config to yaml file
    dump_config('register_custom_value.yaml', read_config_from_object(app))
    print(f'point is: {app.point}')

    # Now we should have a custom_value_example.yaml file with the contents:
    """
    name: ''
    point: !tree_config_example_point [11, 34]
    """

    # load config and apply it
    apply_config(app, load_config(app, 'register_custom_value.yaml'))
    print(f'point is: {app.point}')

    # when run, this prints:
    """
    point is: Point(x=11, y=34)
    point is: Point(x=11, y=34)
    """
