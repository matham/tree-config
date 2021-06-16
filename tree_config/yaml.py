"""Yaml module
==============

Provides the functions to create yaml objects, and to dump and load yaml
using these objects.
"""

from typing import Any, Callable
from io import StringIO
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml import Representer, BaseConstructor, BaseRepresenter, \
    SafeRepresenter


__all__ = (
    'get_yaml', 'yaml_dumps', 'yaml_loads', 'register_numpy_yaml_support',
    'register_torch_yaml_support', 'register_kivy_yaml_support',
    'register_pathlib_yaml_support'
)


def get_yaml() -> YAML:
    """Creates and returns a yaml object that can be used by
    :func:`yaml_dumps` and :func:`yaml_loads` to dump and load from yaml files.

    The default flow style (``default_flow_style``) is set to False so the file
    is formatted as expanded. The yaml type instantiated is ``safe``.
    """
    yaml = YAML(typ='safe')
    yaml.default_flow_style = False
    return yaml


def yaml_dumps(value: Any, get_yaml_obj: Callable[[], YAML] = get_yaml) -> str:
    """Converts the object to yaml.

    :param value: the object to convert.
    :param get_yaml_obj: A function such as :func:`get_yaml` that will be called
        to get a yaml object. Defaults to :func:`get_yaml`.
    :return: a string yaml representation.
    """
    yaml = get_yaml_obj()
    s = StringIO()
    yaml.dump(value, s)
    return s.getvalue()


def yaml_loads(value: str, get_yaml_obj: Callable[[], YAML] = get_yaml) -> Any:
    """Loads a yaml file and converts it to the objects it represents.

    :param value: the string to decode.
    :param get_yaml_obj: A function such as :func:`get_yaml` that will be called
        to get a yaml object. Defaults to :func:`get_yaml`.
    :return: the decoded object.
    """
    yaml = get_yaml_obj()
    return yaml.load(value)


def _represent_numpy_array(representer: Representer, val):
    return representer.represent_sequence(
        f'!tree_numpy_array_{val.dtype.str}', val.tolist())


def _represent_numpy_number(representer: Representer, val):
    return representer.represent_sequence(
        f'!tree_numpy_num_{val.dtype.str}', (val.item(), ))


def _numpy_array_constructor(constructor: BaseConstructor, tag_suffix, node):
    import numpy
    return numpy.asarray(
        constructor.construct_sequence(node, deep=True),
        dtype=numpy.dtype(tag_suffix))


def _numpy_number_constructor(constructor: BaseConstructor, tag_suffix, node):
    import numpy
    return numpy.dtype(tag_suffix).type(constructor.construct_sequence(node)[0])


def _represent_torch(representer: Representer, val):
    dtype = str(val.dtype)[6:]
    if len(val.shape):
        return representer.represent_sequence(
            f'!tree_torch_array_{dtype}', val.tolist())

    return representer.represent_sequence(
        f'!tree_torch_num_{dtype}', (val.tolist(), ))


def _torch_array_constructor(constructor: BaseConstructor, tag_suffix, node):
    import torch
    return torch.as_tensor(
        constructor.construct_sequence(node, deep=True),
        dtype=getattr(torch, tag_suffix))


def _torch_num_constructor(constructor: BaseConstructor, tag_suffix, node):
    import torch
    return torch.as_tensor(
        constructor.construct_sequence(node, deep=True)[0],
        dtype=getattr(torch, tag_suffix))


def register_torch_yaml_support() -> None:
    """Registers the torch data types so it can be encoded to yaml and then
    decoded.

    When it is encountered in an object it is converted to a list
    with a special torch tag. When decoded, an appropriate torch type is
    constructed and returned.
    """
    import torch
    BaseRepresenter.add_multi_representer(torch.Tensor, _represent_torch)

    BaseConstructor.add_multi_constructor(
        '!tree_torch_array_', _torch_array_constructor)
    BaseConstructor.add_multi_constructor(
        '!tree_torch_num_', _torch_num_constructor)


def register_numpy_yaml_support() -> None:
    """Registers the numpy data types so it can be encoded to yaml and then
    decoded.

    When it is encountered in an object it is converted to a list
    with a special numpy tag. When decoded, an appropriate numpy type is
    constructed and returned.
    """
    import numpy
    BaseRepresenter.add_multi_representer(numpy.ndarray, _represent_numpy_array)
    BaseRepresenter.add_multi_representer(numpy.number, _represent_numpy_number)

    BaseConstructor.add_multi_constructor(
        '!tree_numpy_array_', _numpy_array_constructor)
    BaseConstructor.add_multi_constructor(
        '!tree_numpy_num_', _numpy_number_constructor)


def _represent_property(representer: SafeRepresenter, data):
    return representer.represent_data(data.defaultvalue)


def register_kivy_yaml_support() -> None:
    """Registers the Kivy properties so it can be encoded to yaml.

    E.g. Some properties create custom list sub-classes.
    """
    from kivy.properties import ObservableDict, ObservableList, Property

    SafeRepresenter.add_multi_representer(
        ObservableList, SafeRepresenter.represent_list)
    SafeRepresenter.add_multi_representer(
        ObservableDict, SafeRepresenter.represent_dict)

    BaseRepresenter.add_multi_representer(Property, _represent_property)


def _represent_path(representer: SafeRepresenter, val):
    return representer.represent_scalar('!tree_path', str(val))


def _path_constructor(constructor: BaseConstructor, tag_suffix, node):
    return Path(node)


def register_pathlib_yaml_support() -> None:
    """Registers pathlib.Path so it can be encoded and decoded back to Path.
    """
    SafeRepresenter.add_multi_representer(Path, _represent_path)
    BaseConstructor.add_multi_constructor('!tree_path', _path_constructor)
