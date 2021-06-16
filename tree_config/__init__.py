"""Configuration
=================

:mod:`tree-config` provides the tools to configure applications where the
objects to be configured are nested in a tree-like fashion such that they
can be represented as nested dicts in e.g. a yaml file.

See the guide for complete examples.
"""

__version__ = '1.0.0'


from typing import Tuple, List, Dict, Any, Union
import os
from pathlib import Path
from inspect import isclass

from .yaml import yaml_dumps, yaml_loads
from .utils import get_class_bases, class_property

__all__ = (
    '__version__',
    'Configurable', 'load_apply_save_config', 'read_config_from_object',
    'read_config_from_file', 'apply_config', 'load_config', 'dump_config',
    'get_config_prop_names', 'get_config_prop_items',
    'get_config_children_names', 'get_config_children_items')


class Configurable:
    """:mod:`tree_config` uses a duck typing approach. E.g. when applying
    config, :func:`apply_config` will call ``apply_config_property`` if it is
    defined for the objects being configured, otherwise it directly sets the
    properties.

    The :class:`Configurable` can be used as a base-class instead of the duck
    typing approach and it defines all the special config methods. It can also
    be used as a guide to the names of the special config hooks available
    when using the duck typing approach.

    There are only two possible benefits to using :class:`Configurable`.
    (1) it defines ``_config_props`` / ``_config_children``
    which caches the names of the configurable properties / children on a
    per-class basis. Unlike the duck typing approach that gathers them afresh
    every time. (2) You can use ``super`` for properties you want to use the
    default handling approach as in the following example.

    However, the main reason for the class' existance is to define the
    configuration API in one place so we can refer to the method names.

    Consider a duck typing example and the inheritance based example:

    .. code-block:: python

        class DuckApp:

            _config_props_ = ('frame', 'color')

            frame = 'square'
            color = 'blue'

        class ConfigurableApp(Configurable):

            _config_props_ = ('frame', 'color')

            frame = 'square'
            color = 'blue'

    Both behave identically with respect to configuration:

    .. code-block:: python

        >>> read_config_from_object(DuckApp())
        {'frame': 'square', 'color': 'blue'}
        >>> read_config_from_object(ConfigurableApp())
        {'frame': 'square', 'color': 'blue'}

    However, if we wanted to customize setting the ``frame`` property, using
    :class:`Configurable` will be slighlty simpler since you can call super
    to set the remaining properties in the default way. E.g.:

    .. code-block:: python

        class DuckApp:

            _config_props_ = ('frame', 'color')

            frame = 'square'

            color = 'blue'

            def apply_config_property(self, name, value):
                if name == 'frame':
                    self.frame = value * 2
                else:
                    setattr(self, name, value)

        class ConfigurableApp(Configurable):

            _config_props_ = ('frame', 'color')

            frame = 'square'

            color = 'blue'

            def apply_config_property(self, name, value):
                if name == 'frame':
                    self.frame = value * 2
                else:
                    super().apply_config_property(name, value)
    """

    _config_props_: Tuple[str] = ()
    """A list of configurable property names of the class that is set/read
    by the configuration API.

    Each sub/super-class can define this and the properties are accumulated
    across all the sub/super-classes.

    :meta public:
    """

    _config_props_cache: List[str] = None

    _config_children_: Dict[str, str] = {}
    """A dict of configurable children objects of the class that is used
    by the configuration API to traverse the configuration "tree" and to
    configure all these objects.

    The keys are the human friendly names of the children and the values are
    the corresponding property names storing the child.

    Each sub/super-class can define this and the children are accumulated
    across all the sub/super-classes.

    :meta public:
    """

    _config_children_cache: Dict[str, str] = None

    @class_property
    def _config_props(cls) -> List[str]:
        """A property, which if defined will be used to get all the configurable
        properties instead of using :attr:`_config_props_`. It returns the
        list of configurable properties like :attr:`_config_props_`.

        :meta public:
        """
        props = cls.__dict__.get('_config_props_cache', None)
        if props is None:
            cls._config_props_cache = props = _get_config_prop_names(cls)
        return props

    @class_property
    def _config_children(cls) -> Dict[str, str]:
        """A property, which if defined will be used to get all the configurable
        children instead of using :attr:`_config_children_`. It returns the
        dict of configurable children like :attr:`_config_children_`.

        :meta public:
        """
        children = cls.__dict__.get('_config_children_cache', None)
        if children is None:
            cls._config_children_cache = children = _get_config_children_names(
                cls)
        return children

    def apply_config_child(
            self, name: str, prop: str, obj: Any, config: Dict[str, Any]
    ) -> Any:
        """If defined, it is called to apply the configuration for all the
        properties of the child, for each child.

        When defined, it must either call :func:`apply_config` which also
        implicitly dispatches :meth:`post_config_applied`. If you manually
        configure the child, you also have to call :meth:`post_config_applied`
        manually.

        :param name: The human friendly name of the child that will be
            configured. It is the same as the keys in :attr:`_config_children_`.
        :param prop: The property name storing the child that will be
            configured. It is the same as the values in
            :attr:`_config_children_`.
        :param obj: The configurable child object.
        :param config: The config dict to be applied to the child.
        """
        apply_config(obj, config)

    def get_config_property(self, name: str) -> Any:
        """If defined, it is called by the configuration system to get the
        value of the named property.

        :param name: The name of the property to get.
        """
        return getattr(self, name)

    def apply_config_property(self, name: str, value: Any) -> None:
        """If defined, it is called to set the value of a configurable property
        of the class.

        :param name: The name of the property.
        :param value: The value of the property.
        """
        setattr(self, name, value)

    def post_config_applied(self) -> None:
        """If defined, it is called by the configuration system when it finishes
        applying all the configuration properties/children of this object.
        """
        pass


def get_config_prop_items(obj_or_cls, get_attr=getattr) -> Dict[str, Any]:
    """Returns a dict mapping the names of all the configurable properties
    of ``obj_or_cls`` to its values as gotten from the object or class.

    We get the list of properties of the object from
    :func:`get_config_prop_names`. For each property, if the object has
    a ``get_config_property``
    method, that is used to get the value. Otherwise, or if it's a class
    ``get_attr`` is used instead.

    :param obj_or_cls: The object or class on which to search for properties.
    :param get_attr: The function to use to get the property value from the
        object. defaults to ``getattr``.

    E.x.:

    .. code-block:: python

        class App:

            _config_props_ = ('name', )

            name = 'chair'

        class MyApp(App):

            _config_props_ = ('location', )

            location = 0

            def get_config_property(self, name):
                if name == 'location':
                    return len(name)
                return getattr(self, name)

    then:

    .. code-block:: python

        >>> get_config_prop_items(MyApp())
        {'location': 8, 'name': 'chair'}
        >>> get_config_prop_items(MyApp)
        {'location': 0, 'name': 'chair'}
    """
    get_config_property = getattr(obj_or_cls, 'get_config_property', None)
    if get_config_property is None or isclass(obj_or_cls):
        return {prop: get_attr(obj_or_cls, prop)
                for prop in get_config_prop_names(obj_or_cls)}

    return {prop: get_config_property(prop)
            for prop in get_config_prop_names(obj_or_cls)}


def get_config_prop_names(obj_or_cls) -> List[str]:
    """Returns a list of the names of all the configurable properties
    of ``obj_or_cls``.

    If ``obj_or_cls`` has a ``_config_props`` property, that is used to get the
    list of configurable properties, otherwise we walk the class and its super
    classes hierarchy using ``_config_props_`` to get the configurable property
    names.

    :param obj_or_cls: The object or class on which to search for properties.

    E.x.:

    .. code-block:: python

        class App:

            _config_props_ = ('name', )

            name = 'chair'

        class MyApp(App):

            _config_props_ = ('location', )

            location = 0

            def get_config_property(self, name):
                if name == 'location':
                    return len(name)
                return getattr(self, name)

    then:

    .. code-block:: python

        >>> get_config_prop_names(MyApp())
        ['location', 'name']
        >>> get_config_prop_names(MyApp)
        ['location', 'name']
    """
    props = getattr(obj_or_cls, '_config_props', None)
    if props is not None:
        return props
    return _get_config_prop_names(obj_or_cls)


def _get_config_prop_names(obj_or_cls) -> List[str]:
    cls = obj_or_cls
    if not isclass(obj_or_cls):
        cls = obj_or_cls.__class__

    props = {}
    for c in [cls] + list(get_class_bases(cls)):
        for prop in c.__dict__.get('_config_props_', ()):
            if prop in props:
                continue

            if not hasattr(obj_or_cls, prop):
                raise Exception(
                    f'Missing attribute <{prop}> from <{obj_or_cls}> '
                    f'in <{cls}>')
            props[prop] = None

    return list(props)


def get_config_children_items(
        obj_or_cls, get_attr=getattr) -> List[Tuple[str, str, Any]]:
    """Returns a list of 3-tuples of all the configurable children
    of ``obj_or_cls``. Each item is is a 3-tuple of
    ``(friendly_name, prop_name, value)``, where ``friendly_name`` is the name
    as listed in the keys of ``_config_children_``, ``prop_name`` is the
    property name in the class as listed in the values of ``_config_children_``,
    and ``value`` is the value taken from ``obj_or_cls``.

    We get the list of children of the object from
    :func:`get_config_children_names`.

    :param obj_or_cls: The object or class on which to search for children.
    :param get_attr: The function to use to get the child value from the
        object. defaults to ``getattr``.

    E.x.:

    .. code-block:: python

        class App:

            _config_children_ = {'the box': 'box'}

            box = None

        class Box:
            pass

    then:

    .. code-block:: python

        >>> get_config_children_items(App())
        [('the box', 'box', None)]
        >>> get_config_children_items(App)
        [('the box', 'box', None)]
        >>> app = App()
        >>> app.box = Box()
        >>> get_config_children_items(app)
        [('the box', 'box', <Box at 0x264581a2a90>)]
    """
    return [
        (name, prop, get_attr(obj_or_cls, prop))
        for name, prop in get_config_children_names(obj_or_cls).items()
    ]


def get_config_children_names(obj_or_cls) -> Dict[str, str]:
    """Returns a dict of the names friendly and property names of all the
    configurable children of ``obj_or_cls``.

    If ``obj_or_cls`` has a ``_config_children`` property, that is used to get
    the list of configurable children, otherwise we walk the class and its super
    classes hierarchy using ``_config_children_`` to get the configurable
    children names.

    :param obj_or_cls: The object or class on which to search for children.

    E.x.:

    .. code-block:: python

        class App:

            _config_children_ = {'the box': 'box'}

            box = None

        class Box:
            pass

    then:

    .. code-block:: python

        >>> get_config_children_names(App())
        {'the box': 'box'}
        >>> get_config_children_names(App)
        {'the box': 'box'}
    """
    children = getattr(obj_or_cls, '_config_children', None)
    if children is not None:
        return children
    return _get_config_children_names(obj_or_cls)


def _get_config_children_names(obj_or_cls) -> Dict[str, str]:
    cls = obj_or_cls
    if not isclass(obj_or_cls):
        cls = obj_or_cls.__class__

    children = {}
    for c in [cls] + list(get_class_bases(cls)):
        for name, prop in c.__dict__.get('_config_children_', {}).items():
            if name in children:
                continue

            if not hasattr(obj_or_cls, prop):
                raise Exception(
                    f'Missing attribute <{prop}> from <{obj_or_cls}> '
                    f'in <{cls}>')
            children[name] = prop

    return children


def _fill_config_from_children(children, config: dict, get_attr):
    for name, prop, obj in children:
        if obj is None:
            continue

        if isinstance(obj, (list, tuple)):
            config[name] = [read_config_from_object(o, get_attr) for o in obj]
        else:
            config[name] = read_config_from_object(obj, get_attr)


def read_config_from_object(obj, get_attr=getattr) -> Dict[str, Any]:
    """Returns a recursive dict containing all the configuration options of the
    obj and its configurable children.

    :param obj: The object from which to get the config.
    :param get_attr: The function to use to get the child value from the
        object and its children. defaults to ``getattr``.

    E.x.:

    .. code-block:: python

        class App:

            _config_props_ = ('name', )

            _config_children_ = {'the box': 'box'}

            name = 'chair'

            box = None

        class Box:

            _config_props_ = ('volume', )

            volume = 12

    then:

    .. code-block:: python

        >>> app = App()
        >>> app.box = Box()
        >>> read_config_from_object(app)
        {'the box': {'volume': 12}, 'name': 'chair'}
    """
    # TODO: break infinite cycle if obj is listed in its nested config classes
    config = {}

    # get all the configurable classes used by the obj
    children = get_config_children_items(obj, get_attr)
    _fill_config_from_children(children, config, get_attr)

    used_keys = {s for name, prop, obj in children for s in (name, prop)}

    for prop, value in get_config_prop_items(obj, get_attr).items():
        if prop not in used_keys:
            config[prop] = value
    return config


def _apply_config_to_children(root_obj, children, config, get_attr, set_attr):
    for name, prop, obj in children:
        if obj is None or name not in config:
            continue

        # todo: handle when obj is a list/dict
        method = getattr(root_obj, 'apply_config_child', None)
        if method is None:
            apply_config(obj, config[name], get_attr, set_attr)
        else:
            method(name, prop, obj, config[name])


def apply_config(
        obj, config: Dict[str, Any], get_attr=getattr, set_attr=setattr
) -> None:
    """Takes the config data read with e.g. :func:`read_config_from_object`
    or :func:`read_config_from_file` and applies
    them to the object and its children.

    Calls ``post_config_applied`` on the object and/or its children after they
    are configured if all/any have such a method.

    :param obj: The object to which to apply the config.
    :param config: The config dict.
    :param get_attr: The function to use to get the child value from the
        object and its children. defaults to ``getattr``.
    :param set_attr: The function to use to set the property values for the
        object and its children. defaults to ``setattr``.

    E.x.:

    .. code-block:: python

        class App:

            _config_props_ = ('name', )

            _config_children_ = {'the box': 'box'}

            name = 'chair'

            box = None

        class Box:

            _config_props_ = ('volume', )

            volume = 12

            def apply_config_property(self, name, value):
                print('applying child', name)
                setattr(self, name, value)

            def post_config_applied(self):
                print('done applying child')

    then:

    .. code-block:: python

        >>> app = App()
        >>> app.box = Box()
        >>> d = read_config_from_object(app)
        >>> d
        {'the box': {'volume': 12}, 'name': 'chair'}
        >>> d['name'] = 'bed'
        >>> d['the box']['volume'] = 34
        >>> apply_config(app, d)
        applying child volume
        done applying child
        >>> app.name
        'bed'
        >>> app.box.volume
        34
    """
    # get all the configurable classes used by the obj
    children = get_config_children_items(obj, get_attr)
    _apply_config_to_children(obj, children, config, get_attr, set_attr)

    used_keys = {s for name, prop, obj in children for s in (name, prop)}

    method = getattr(obj, 'apply_config_property', None)
    if method is None:
        for k, v in config.items():
            if k not in used_keys:
                set_attr(obj, k, v)
    else:
        for k, v in config.items():
            if k not in used_keys:
                method(k, v)

    post_config_applied = getattr(obj, 'post_config_applied', None)
    if post_config_applied is not None:
        post_config_applied()


def read_config_from_file(
        filename: Union[str, Path], yaml_load_str=yaml_loads) -> Dict[str, Any]:
    """Reads and returns the yaml config data dict from a file that was
    previously dumped with :func:`dump_config`.

    :param filename: The yaml filename.
    :param yaml_load_str: The function to parse the yaml string read from the
        file. Defaults to :func:`~tree_config.utils.yaml_loads`.

    E.g.:

    .. code-block:: python

        >>> class App:
        >>>     _config_props_ = ('name', )
        >>>     name = 'chair'
        >>> app = App()
        >>> d = read_config_from_object(app)
        >>> dump_config('config.yaml', d)
        >>> read_config_from_file('config.yaml')
        {'name': 'chair'}
    """
    with open(filename) as fh:
        opts = yaml_load_str(fh.read())
    if opts is None:
        opts = {}
    return opts


def load_config(
        obj, filename: Union[str, Path], get_attr=getattr,
        yaml_dump_str=yaml_dumps, yaml_load_str=yaml_loads) -> Dict[str, Any]:
    """Loads and decodes the config from a yaml file. If the config file doesn't
    exist, it first dumps the config to the file using
    :func:`read_config_from_object` and :func:`dump_config` before loading it.

    :param obj: The object from which to dump the config when the files doesn't
        exist.
    :param filename: The yaml filename.
    :param get_attr: The function to use to get the property/children values
        from the object. defaults to ``getattr``.
    :param yaml_dump_str: The function to encode the config to yaml. Defaults
        to :func:`~tree_config.utils.yaml_dumps`.
    :param yaml_load_str: The function to parse the yaml string read from the
        file. Defaults to :func:`~tree_config.utils.yaml_loads`.

    E.g.:

    .. code-block:: python

        >>> class App:
        >>>     _config_props_ = ('name', )
        >>>     name = 'chair'
        >>> load_config(App(), 'app_config.yaml')
        {'name': 'chair'}
    """
    if not os.path.exists(filename):
        dump_config(
            filename, read_config_from_object(obj, get_attr),
            yaml_dump_str=yaml_dump_str)

    return read_config_from_file(filename, yaml_load_str=yaml_load_str)


def dump_config(
        filename: Union[str, Path], data: Dict[str, Any],
        yaml_dump_str=yaml_dumps) -> None:
    """Dumps config data gotten with e.g. :func:`read_config_from_object`
    to a yaml file.

    :param filename: The yaml filename.
    :param data: The config data.
    :param yaml_dump_str: The function to encode the config to yaml. Defaults
        to :func:`~tree_config.utils.yaml_dumps`.

    E.g.:

    .. code-block:: python

        >>> class App:
        >>>     _config_props_ = ('name', )
        >>>     name = 'chair'
        >>> app = App()
        >>> d = read_config_from_object(app)
        >>> dump_config('config.yaml', d)
        >>> with open('config.yaml') as fh:
        ...     print(fh.read())

    Which prints ``name: chair``.
    """
    with open(filename, 'w') as fh:
        fh.write(yaml_dump_str(data))


def load_apply_save_config(
        obj, filename: Union[str, Path], get_attr=getattr, set_attr=setattr,
        yaml_dump_str=yaml_dumps, yaml_load_str=yaml_loads) -> Dict[str, Any]:
    """Applies the config to the object from the yaml file (if the file doesn't
    exist it creates it), and then dumps to the yaml file the current config
    from the object. It also returns the final config dict.

    This can be used to set the object from the config, but also making sure the
    file contains the current config including any new properties not previously
    there or properties that changed during config application.

    :param obj: The configurable object.
    :param filename: The yaml filename.
    :param get_attr: The function to use to get the property/children values
        from the object. defaults to ``getattr``.
    :param set_attr: The function to use to set the property values of the
        object and its children. defaults to ``setattr``.
    :param yaml_dump_str: The function to encode the config to yaml. Defaults
        to :func:`~tree_config.utils.yaml_dumps`.
    :param yaml_load_str: The function to parse the yaml string read from the
        file. Defaults to :func:`~tree_config.utils.yaml_loads`.

    E.x.:

    .. code-block:: python

        class App:

            _config_props_ = ('name', )

            name = 'chair'

        class AppV2:

            _config_props_ = ('name', 'side')

            name = 'chair'

            side = 'left'

    then:

    .. code-block:: python

        >>> app = App()
        >>> app.name = 'tree'
        >>> load_apply_save_config(app, 'config_app.yaml')
        {'name': 'tree'}
        >>> app.name
        'tree'
        >>> # then later for v2 of the app
        >>> app_v2 = AppV2()
        >>> app_v2.name
        'chair'
        >>> load_apply_save_config(app_v2, 'config_app.yaml')
        {'name': 'tree', 'side': 'left'}
        >>> app_v2.name
        'tree'
        >>> with open('config_app.yaml') as fh:
        ...     print(fh.read())

    this prints::

        name: tree
        side: left
    """
    config = load_config(
        obj, filename, get_attr, yaml_dump_str=yaml_dump_str,
        yaml_load_str=yaml_load_str)
    apply_config(obj, config, get_attr, set_attr)

    config = read_config_from_object(obj, get_attr)
    dump_config(filename, config, yaml_dump_str=yaml_dump_str)
    return config
