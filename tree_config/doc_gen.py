"""Documentation generation
============================

When generating docs, the documentation of the properties listed in
``__config_props__`` can dumped to a yaml file using
:func:`create_doc_listener`.

:func:`write_config_props_rst` can load the docstrings from this yaml file
and then generate a nicely formatted rst file listing all the configurable
properties of the project. See the user guide for details and complete examples.

Command line
------------

This module provides two command line options that can call either
:func:`download_merge_yaml_doc` or :func:`merge_yaml_doc` and forwards the
arguments to these functions. See the guide for examples.
"""

from inspect import isclass
import os.path
from typing import Tuple, List, Dict, Any
import operator
import urllib.request
from collections import deque

from .utils import get_class_bases, get_class_annotations, yaml_loads, \
    yaml_dumps
from tree_config import get_config_children_names

__all__ = (
    'create_doc_listener', 'write_config_props_rst', 'download_merge_yaml_doc',
    'merge_yaml_doc',
)


def _get_config_children_objects(
        obj_or_cls, get_attr=getattr) -> List[Tuple[str, str, Any]]:
    annotations = get_class_annotations(obj_or_cls)
    objects = []
    for name, prop in get_config_children_names(obj_or_cls).items():
        obj = get_attr(obj_or_cls, prop)

        if obj is None:
            # try searching annotations for type
            obj = annotations.get(prop, None)
            if obj is not None:
                # only accept typing generic that is a list/tuple
                args = getattr(obj, '__args__', None)
                if getattr(obj, '__origin__', None) in (list, tuple) and \
                        args is not None and isinstance(args, (list, tuple)) \
                        and len(args) == 1:
                    obj = args[0]

        if obj is not None:
            objects.append((name, prop, obj))
    return objects


def _get_config_prop_items_class(
        obj_or_cls, get_attr=getattr) -> Dict[str, List[Tuple[str, Any]]]:
    cls = obj_or_cls
    if not isclass(obj_or_cls):
        cls = obj_or_cls.__class__

    classes = {}
    for c in [cls] + list(get_class_bases(cls)):
        cls_name = f'{c.__module__}.{c.__name__}'
        cls_props = {}
        for prop in c.__dict__.get('_config_props_', ()):
            if prop in cls_props:
                continue

            if not hasattr(cls, prop):
                raise Exception('Missing attribute <{}> in <{}>'.
                                format(prop, cls.__name__))

            cls_props[prop] = get_attr(cls, prop)

        if cls_props:
            classes[cls_name] = list(cls_props.items())

    return classes


def create_doc_listener(
        sphinx_app, package_name, filename, yaml_dump_str=yaml_dumps):
    """Creates a listener for the ``__config_props__`` attributes and dumps
    the docs of any props listed, to ``filename``. If the file
    already exists, it extends it with new data and overwrites any exiting
    properties that we see again in this run.

    To use, in the sphinx conf.py file do something like::

        def setup(app):
            import package
            create_doc_listener(app, package, 'config_attrs.yaml')

    where ``package`` is the package for which the docs are generated.

    See the guide for a full example.
    """
    try:
        with open(filename) as fh:
            data = yaml_loads(fh.read())
    except IOError:
        data = {}

    def config_attrs_doc_listener(app, what, name, obj, options, lines):
        if not name.startswith(package_name):
            return

        if what == 'class':
            props = obj.__dict__.get('_config_props_', ())
            # ew haven't seen this class before
            if name not in data:
                # just add items for all props
                data[name] = {n: [] for n in props}
            else:
                # we have seen this class, add only missing props
                cls_data = data[name]
                for n in props:
                    if n not in cls_data:
                        cls_data[n] = []
        elif what == 'attribute':
            # now that we saw the class, we fill in the prop docs
            parts = name.split('.')  # parts of the prop path x.Class.prop
            cls = '.'.join(parts[:-1])  # full class path x.Class
            # we have seen the class and prop?
            if cls in data and parts[-1] in data[cls]:
                data[cls][parts[-1]] = lines

    def dump_config_attrs_doc(app, exception):
        # dump config docs
        filtered_data = {
            name: {n: lines for n, lines in props.items() if lines}
            for name, props in data.items()}
        filtered_data = {
            name: props for name, props in filtered_data.items() if props}

        with open(filename, 'w') as fh_:
            fh_.write(yaml_dump_str(filtered_data))

    sphinx_app.connect('autodoc-process-docstring', config_attrs_doc_listener)
    sphinx_app.connect('build-finished', dump_config_attrs_doc)


def _walk_config_classes_flat(obj, get_attr=getattr):
    classes_flat = []  # stores all the configurable classes
    stack = deque([(-1, '', obj)])

    while stack:
        level, name, obj = stack.popleft()
        # now we "visited" obj
        classes_flat.append((level, name, obj, {}, {}))

        children = _get_config_children_objects(obj, get_attr=get_attr)

        for child_name, child_prop, child_obj in sorted(
                children, key=lambda x: x[0]):
            if isinstance(child_obj, (list, tuple)):
                for i, o in enumerate(child_obj):
                    stack.appendleft((
                        level + 1, '{} --- {}'.format(child_name, i), o))
            else:
                stack.appendleft((level + 1, child_name, child_obj))

    assert len(classes_flat) >= 1
    return classes_flat


def _get_config_attrs_doc(obj, filename, get_attr=getattr):
    """Objects is a dict of object (class) paths and keys are the names of the
    config attributes of the class.
    """
    classes_flat = _walk_config_classes_flat(obj, get_attr=get_attr)

    # get the modules associated with each of the classes
    for _, _, obj, classes_props, _ in classes_flat:
        # get all the parent classes of the class and their props
        for cls, props in _get_config_prop_items_class(obj).items():
            classes_props[cls] = {prop: [val, None] for prop, val in props}

    # get the saved docs
    with open(filename) as fh:
        docs = yaml_loads(fh.read())

    # mapping of class name to a mapping of class props to their docs
    for level, name, obj, classes_props, props_docs in classes_flat:
        for cls, props in classes_props.items():
            cls_docs = docs.get(cls, {})
            for prop in props:
                props[prop][1] = cls_docs.get(prop, [])
                props_docs[prop] = props[prop]
    return classes_flat


def write_config_props_rst(
        obj, project, app, exception, filename, rst_filename,
        get_attr=getattr, yaml_dump_str=yaml_dumps):
    """Walks through all the configurable classes of ``obj``, recursively
    by looking at ``_config_props_`` and ``_config_children_`` and using the
    type hints of these children properties if they are None (e.g. if obj is a
    class). For each property it loads their docs from the yaml file
    ``filename`` and it generates a rst output file at ``rst_filename`` with
    all the tokens.

    For example in the sphinx conf.py file do::

        def setup(app):
            app.connect('build-finished', partial(write_config_props_rst, \
ProjectApp, project_name, filename='config_prop_docs.yaml', \
rst_filename='source/config.rst'))

    where project_name is the name of project and ProjectApp is the App of the
    package the contains all the configurable objects.

    See the guide for a complete example.
    """
    headings = [
        '-', '`', ':', "'", '"', '~', '^', '_', '*', '+', '#', '<', '>']
    n = len(headings) - 1

    # get the docs for the props
    classes_flat = _get_config_attrs_doc(obj, filename, get_attr)

    header = '{} Config'.format(project.upper())
    lines = [
        header, '=' * len(header), '',
        'The following are the configuration options provided by the app. '
        'It can be configured by changing appropriate values in the '
        '``config.yaml`` settings file. The options default to the default '
        'value of the classes for each of the options.', '']

    for level, name, _, _, props_docs in classes_flat:
        if level >= 0:
            lines.append(name)
            lines.append(headings[min(level, n)] * len(name))
            lines.append('')
        for prop, (default, doc) in sorted(
                props_docs.items(), key=operator.itemgetter(0)):

            lines.append(f'`{prop}`:')

            default = yaml_dump_str(default).strip().rstrip(' .\n\r')
            default_lines = default.splitlines()
            if len(default_lines):
                lines.append(' Default value::')
                lines.append('')
                for line in default_lines:
                    lines.append(f'  {line}')
                lines.append('')

            while doc and not doc[-1].strip():
                del doc[-1]

            lines.extend([' ' + d for d in doc if d])
            lines.append('')
        lines.append('')

    lines = '\n'.join(lines)
    try:
        with open(rst_filename) as fh:
            if fh.read() == lines:
                return
    except IOError:
        pass

    with open(rst_filename, 'w') as fh:
        fh.write(lines)


def download_merge_yaml_doc(filename, url, out_filename):
    """Downloads a yaml file with previously saved configurable properties
    docstrings, optionally merges it with an existing docstrings yaml file, and
    outputs the merged yaml file. See the guide for an example.

    :param filename: The optional yaml filename into which to merge the remote
        yaml docstrings.
    :param url: A url to a docstrings containing yaml file that will be
        downloaded and optionally merged into ``filename`` and output to
        ``out_filename``.
    :param out_filename: The filename of the output yaml file.

    On the command line it's invocated as::

        $ python -m tree_config.doc_gen download --help
        usage: Config Docs generation download [-h] [-f FILENAME] -u URL -o
                                               OUT_FILENAME

        optional arguments:
          -h, --help            show this help message and exit
          -f FILENAME, --filename FILENAME
                                The optional yaml filename with which to merge
                                the downloaded file.
          -u URL, --url URL
          -o OUT_FILENAME, --out_filename OUT_FILENAME
    """
    with urllib.request.urlopen(url) as f:
        remote = yaml_loads(f.read())

    local = {}
    if filename and os.path.exists(filename):
        with open(filename) as f:
            local = yaml_loads(f)

    local.update(remote)
    with open(out_filename, 'w') as f:
        f.write(yaml_dumps(local))


def merge_yaml_doc(filename1, filename2, out_filename):
    """Merges two yaml files containing configurable properties docstrings into
    a single output yaml file.

    :param filename1: First yaml input filename into which the second is merged.
    :param filename2: Second yaml input filename.
    :param out_filename: The output filename of the resulting yaml file.

    On the command line it's invocated as::

        $ python -m tree_config.doc_gen merge --help
        usage: Config Docs generation merge [-h] -f1 FILENAME1 -f2 FILENAME2 -o
                                            OUT_FILENAME

        optional arguments:
          -h, --help            show this help message and exit
          -f1 FILENAME1, --filename1 FILENAME1
          -f2 FILENAME2, --filename2 FILENAME2
          -o OUT_FILENAME, --out_filename OUT_FILENAME
    """
    with open(filename1) as f:
        data = yaml_loads(f.read())

    with open(filename2) as f:
        data.update(yaml_loads(f.read()))

    with open(out_filename, 'w') as f:
        f.write(yaml_dumps(data))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(prog='Config Docs generation')
    subparsers = parser.add_subparsers(dest='command')

    download = subparsers.add_parser(
        'download',
        help='Runs download_merge_yaml_doc to download the yaml file, merge '
             'it with filename, and outputs the result.')
    download.add_argument(
        '-f', '--filename', default=None,
        help='The optional yaml filename with which to merge the downloaded '
             'file.')
    download.add_argument('-u', '--url', required=True)
    download.add_argument('-o', '--out_filename', required=True)

    download = subparsers.add_parser(
        'merge',
        help='Merge the two yaml file containing the docstrings into a '
             'single file.')
    download.add_argument('-f1', '--filename1', required=True)
    download.add_argument('-f2', '--filename2', required=True)
    download.add_argument('-o', '--out_filename', required=True)

    args = parser.parse_args()

    if args.command == 'download':
        download_merge_yaml_doc(args.filename, args.url, args.out_filename)
    elif args.command == 'merge':
        merge_yaml_doc(args.filename1, args.filename2, args.out_filename)
