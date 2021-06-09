from typing import Any, Callable
from io import StringIO
from ruamel.yaml import YAML
from ruamel.yaml import Representer, BaseConstructor, BaseRepresenter


__all__ = ('get_yaml', 'yaml_dumps', 'yaml_loads')


def get_yaml() -> YAML:
    yaml = YAML(typ='safe')
    yaml.default_flow_style = False
    return yaml


def yaml_dumps(value: Any, get_yaml_obj: Callable[[], YAML] = get_yaml) -> str:
    yaml = get_yaml_obj()
    s = StringIO()
    yaml.dump(value, s)
    return s.getvalue()


def yaml_loads(value: str, get_yaml_obj: Callable[[], YAML] = get_yaml) -> Any:
    yaml = get_yaml_obj()
    return yaml.load(value)


def _represent_torch(representer: Representer, val):
    return representer.represent_sequence(
        f'!sapinet_torch_{val.dtype}', val.tolist())


def _represent_numpy(representer: Representer, val):
    return representer.represent_sequence(
        f'!sapinet_numpy_{val.dtype}', val.tolist())


def _get_torch_constructor(cls):
    def load(constructor: BaseConstructor, node):
        return cls(constructor.construct_sequence(node))
    return load


def register_torch_yaml_support() -> None:
    import torch
    tensors = {
        'float': torch.FloatTensor,
        'float32': torch.FloatTensor,
        'double': torch.DoubleTensor,
        'float64': torch.DoubleTensor,
        'half': torch.HalfTensor,
        'float16': torch.HalfTensor,
        'uint8': torch.ByteTensor,
        'int8': torch.CharTensor,
        'short': torch.ShortTensor,
        'int16': torch.ShortTensor,
        'int': torch.IntTensor,
        'int32': torch.IntTensor,
        'long': torch.LongTensor,
        'int64': torch.LongTensor,
        'bool': torch.BoolTensor,
    }
    for dtype, cls in tensors.items():
        tag = f'!sapinet_torch_{dtype}'
        BaseConstructor.add_multi_constructor(tag, _get_torch_constructor(cls))

    BaseRepresenter.add_multi_representer(torch.Tensor, _represent_torch)


def register_numpy_yaml_support() -> None:
    import numpy
    BaseRepresenter.add_multi_representer(numpy.ndarray, _represent_numpy)
