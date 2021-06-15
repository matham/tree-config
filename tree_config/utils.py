"""Utils
========

"""
import functools
from inspect import isclass
import sys
import types
from typing import Dict, Any, Type, Generator, Union
from tree_config.yaml import get_yaml, yaml_loads, yaml_dumps
try:
    from inspect import get_annotations
except ImportError:
    def get_annotations(cls, eval_str):
        # copied from inspect
        obj_dict = getattr(cls, '__dict__', None)
        if obj_dict and hasattr(obj_dict, 'get'):
            ann = obj_dict.get('__annotations__', None)
            if isinstance(ann, types.GetSetDescriptorType):
                ann = None
        else:
            ann = None
        ann = dict(ann) if ann else {}

        if eval_str:
            globals = None
            module_name = getattr(cls, '__module__', None)
            if module_name:
                module = sys.modules.get(module_name, None)
                if module:
                    globals = getattr(module, '__dict__', None)
            locals = dict(vars(cls))

            unwrap = cls
            while True:
                if hasattr(unwrap, '__wrapped__'):
                    unwrap = unwrap.__wrapped__
                    continue
                if isinstance(unwrap, functools.partial):
                    unwrap = unwrap.func
                    continue
                break
            if hasattr(unwrap, "__globals__"):
                globals = unwrap.__globals__

            for key, value in ann.items():
                if isinstance(value, str):
                    ann[key] = eval(value, globals, locals)

        return ann

__all__ = (
    'get_class_bases', 'get_class_annotations', 'class_property')


def get_class_bases(cls: Type) -> Generator[Type, None, None]:
    """Yields all the base-classes of the class, not including the passed class
    or object.
    """
    for base in cls.__bases__:
        if base.__name__ == 'object':
            break
        for cbase in get_class_bases(base):
            yield cbase
        yield base


def get_class_annotations(obj_or_cls: Union[Any, Type[Any]]) -> Dict[str, Any]:
    """Gets a dict of all the annotations of the object/class, including from
    all superclasses. The values are actual object, even if the type is given
    as a string (for forward declarations).
    """
    cls = obj_or_cls
    if not isclass(obj_or_cls):
        cls = obj_or_cls.__class__

    annotations = {}
    for c in [cls] + list(get_class_bases(cls)):
        annotations.update(get_annotations(c, eval_str=True))
    return annotations


class class_property(property):
    """Can be used as ``@class_property`` on a method to make it a class
     property in the same way ``@property`` can be used on a normal method
     to make it a object property.
    """
    def __get__(self, cls, owner):
        return classmethod(self.fget).__get__(None, owner)()
