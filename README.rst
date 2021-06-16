tree-config
===========

Configuration of objects that are nested in a tree-like fashion.

For more information: https://matham.github.io/tree-config/index.html

.. image:: https://img.shields.io/pypi/pyversions/tree-config.svg
    :target: https://pypi.python.org/pypi/tree-config/
    :alt: Supported Python versions

.. image:: https://img.shields.io/pypi/v/tree-config.svg
    :target: https://pypi.python.org/pypi/tree-config/
    :alt: Latest Version on PyPI

.. image:: https://coveralls.io/repos/github/matham/tree-config/badge.svg?branch=main
    :target: https://coveralls.io/github/matham/tree-config?branch=main
    :alt: Coverage status

.. image:: https://github.com/matham/tree-config/workflows/Python%20application/badge.svg
    :target: https://github.com/matham/tree-config/actions
    :alt: Github action status

Installation
============

``tree-config`` can be installed with:

.. code-block:: shell

    pip install tree-config

Configuration usage
===================

``tree-config`` can dump all the configurable properties of all your classes to
a yaml file and then load the the file and restore/apply the values to the
properties. E.g.:

.. code-block:: python

    class App:

        _config_props_ = ('name', )

        _config_children_ = {'app panel': 'panel'}

        def __init__(self):
            self.name = 'Desk'
            self.panel = AppPanel()

    class AppPanel:

        _config_props_ = ('color', )

        color = 'A4FF67'

will automatically configure ``name`` and ``color``.

Following is a guide by example of the multiples ways to control the configuration.
See the `configuration API <https://matham.github.io/tree-config/api.html>`_, including
the ``Configuration`` class for complete details.

See the examples directory in the repo for complete runnable code of the following
examples.

Basic properties
----------------

This example has an app class that contains two panels that are configurable.
``_config_props_`` lists the configurable properties for the class, while
``_config_children_`` constructs the tree of objects that are configurable.

.. code-block:: python

    class App:

        _config_props_ = ('size', 'name')

        _config_children_ = {'app panel': 'panel1', 'home panel': 'panel2'}

        def __init__(self):
            self.size = 12
            self.name = 'Desk'

            self.panel1 = AppPanel()
            self.panel2 = HomePanel()


    class AppPanel:

        _config_props_ = ('color', )

        color = 'A4FF67'


    class HomePanel:

        _config_props_ = ('shape', )

        shape = 'circle'

Then, running:

.. code-block:: python

    from tree_config import dump_config, read_config_from_object
    app = App()
    dump_config('basic_example.yaml', read_config_from_object(app))
    print(f'Shape is: {app.panel2.shape}')

creates a ``basic_example.yaml`` file with the following contents:

.. code-block:: yaml

    app panel: {color: A4FF67}
    home panel: {shape: circle}
    name: Desk
    size: 12

and it prints ``Shape is: circle``. If we want to load a previous yaml file,
where say the shape was ``"square"`` and apply it to the instance, we do:

.. code-block:: python

    from tree_config import load_config, apply_config
    app = App()
    apply_config(app, load_config(app, 'basic_example.yaml'))
    print(f'Shape is: {app.panel2.shape}')

This in turn prints ``Shape is: square``.

Hooking property discovery
--------------------------

``_config_props_`` and ``_config_children_`` are defined on a class, not on
instances. When ``tree-config`` uses them, it will walk the whole class
hierarchy and accumulate their values from all super classes because a
sub-class does not overwrite them, but rather adds to them.

If ``_config_props`` and/or ``_config_children`` is defined on a
class or instance, tree-config will use that value directly, instead of
walking ``_config_props_`` and/or ``_config_children_``, respectively.

E.g. the following code:

.. code-block:: python

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

when run with:

.. code-block:: python

    app = App()
    # now get and save config to yaml file
    dump_config('hook_properties.yaml', read_config_from_object(app))

will generate this yaml file:

.. code-block:: yaml

    app panel:
      color: A4FF67
      name: Desk
      size: 12
    home panel:
      group: window
      size: 12

Notice how ``app panel`` contains the properties
of both ``RootPanel`` and ``AppPanel``, while ``home panel`` only has the
properties listed in ``_config_props``. ``_config_children`` behaves
similarly.

Custom values hooks
-------------------

We may wish to hook the property getting/setting process to
change the value before it is saved or before it is applied again.

E.g. consider that we have a property that stores a namedtuple that we need
to dump as a list (because yaml doesn't understand named tuple) and create
a named tuple again when restoring. ``get_config_property`` and
``apply_config_property`` are the needed hook methods, that are
automatically used if present in the class:

.. code-block:: python

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

Then, running:

.. code-block:: python

    from tree_config import dump_config, read_config_from_object
    app = App()
    dump_config('custom_value_example.yaml', read_config_from_object(app))
    print(f'point is: {app.point}')

creates a ``custom_value_example.yaml`` file with the following contents:

.. code-block:: yaml

    name: ''
    point: [11, 34]

and it prints ``point is: Point(x=11, y=34)``. If we want to load and apply the
yaml file again, we do:

.. code-block:: python

    from tree_config import load_config, apply_config
    app = App()
    apply_config(app, load_config(app, 'custom_value_example.yaml'))
    print(f'point is: {app.point}')

This in turn prints again ``point is: Point(x=11, y=34)``.

See also ``apply_config_child`` for similarly hooking into applying the children
objects. The default, when not provided is to use ``apply_config``, so if
overriding, that should probably also be used for the base case.

Custom tags (pickling)
^^^^^^^^^^^^^^^^^^^^^^

Yaml offers support for representing arbitrary objects using custom tags in the
file. This enables global support for the objects, without having to use
``get_config_property`` / ``apply_config_property`` wherever they are used.

Using the point example above:

.. code-block:: python

    from collections import namedtuple
    from tree_config import dump_config, load_config, apply_config, \
        read_config_from_object
    from ruamel.yaml import BaseConstructor, BaseRepresenter

    Point = namedtuple('Point', ['x', 'y'])

    yaml_tag = '!tree_config_example_point'

    # encoder
    def _represent_point(representer: BaseRepresenter, val):
        return representer.represent_sequence(yaml_tag, tuple(val))

    # decoder
    def _construct_point(constructor: BaseConstructor, tag, node):
        return Point(*constructor.construct_sequence(node))

    # tell yaml how to represent a Point
    def register_point_yaml_support() -> None:
        BaseRepresenter.add_multi_representer(Point, _represent_point)
        BaseConstructor.add_multi_constructor(yaml_tag, _construct_point)


    class App:

        _config_props_ = ('point', 'name')

        point = Point(11, 34)

        name = ''

Now, call:

.. code-block:: python

    register_point_yaml_support()

before running the tree-config dumping/loading code from the last section and
it will generate a yaml file with contents:

.. code-block:: yaml

    name: ''
    point: !tree_config_example_point [11, 34]

See also ``yaml_dumps`` and ``yaml_loads`` for additional customization.
Most functions take a ``yaml_dump_str`` / ``yaml_load_str`` to allow further
customizing the yaml objects. See also ``register_torch_yaml_support``
in ``tree_config.yaml`` for a more complete example as well as some built-in
optional representers that can be registered directly.

Post-applying dispatch
----------------------

After applying configuration to a object and its children objects,
tree-config will call the ``post_config_applied`` method of the object, if
the method exists. E.g.:

.. code-block:: python

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

Then, saving and again applying the yaml using:

.. code-block:: python

    # create app and set properties
    app = App()

    # now get and save config to yaml file
    dump_config('post_apply_dispatch.yaml', read_config_from_object(app))
    # load config and apply it
    apply_config(app, load_config(app, 'post_apply_dispatch.yaml'))

prints the following::

    applying color
    done applying panel
    applying name
    applying size
    done applying app

Configurable class
------------------

The above examples used a duck typing approach to these special configuration/hook
methods, and any/all of these methods were optional. tree-config also offers a
``Configurable`` superclass that defines all these methods with appropriate
default values.

There's no benefit to inheriting from ``Configurable``, but it does provide a
baseclass listing all the special configuration methods. Additionally,
it does cache the list of properties/config children for each class,
so once looked up, it does not need to walk the tree, unlike the duck
typing approach that re-computes at every save/apply.

Auto docs
=========

In addition to configuration, tree-config can also hook into the sphinx doc
generating build steps and generate docs listing all the properties that
can be configured by the application and show the doc string for each of them.
This is helpful to users who want to configure these properties using the
configuration yaml file.

The example directory has a complete doc example.

Given a root object (e.g. App in the examples), we can add callbacks in
``conf.py`` that is called by sphinx as it encounters properties listed in
``_config_props_``. The callback then saves the doc strings of these properties
into a yaml file.

Subsequently, when the build is done, tree-config can go through all the
configurable properties and starting from the root object or class, extract
the doc strings from the yaml file, and create a rst file of those docstrings.

E.g. starting with this code in :

.. code-block:: python

    class App:
        """The app."""

        _config_props_ = ('size', 'name')

        _config_children_ = {'app panel': 'panel1', 'home panel': 'panel2'}

        size = 55
        """Some filename."""

        name = ''
        """Some name."""

        panel1: 'AppPanel' = None
        """The app panel."""

        panel2: 'HomePanel' = None
        """The home panel."""

        def __init__(self, size, name, color, shape):
            self.size = size
            self.name = name

            self.panel1 = AppPanel()
            self.panel1.color = color
            self.panel2 = HomePanel()
            self.panel2.shape = shape


    class AppPanel:
        """The app panel."""

        _config_props_ = ('color', )

        color = ''
        """Color of the app."""


    class HomePanel:
        """The home panel."""

        _config_props_ = ('shape', )

        shape = ''
        """Shape of the home."""

then, we add the following to the top of the ``conf.py`` file:

.. code-block:: python

    import os
    import sys
    from functools import partial
    sys.path.insert(0, os.path.abspath('../'))
    from config_example import App
    from tree_config.doc_gen import create_doc_listener, write_config_props_rst

the exact path added to ``sys.path`` depends on where the code is, or if it's a python
package that is not needed because it's already installed.

We also need to add ``'sphinx.ext.autodoc'`` to the list of extensions. Finally,
at the end of ``conf.py`` add:

.. code-block:: python

    def setup(app):
        # dump all config_example package/subpackages config docstrings to config_prop_docs.yaml
        create_doc_listener(app, 'config_example', 'config_prop_docs.yaml')

        # then get docstrings from yaml file, walk all config properties from App and
        # dump formatted config docs to source/config.rst
        app.connect(
            'build-finished', partial(
                write_config_props_rst, App, 'config_example',
                filename='config_prop_docs.yaml', rst_filename='source/config.rst')
        )

Finally, to the sphinx generated ``index.rst`` we added ``config.rst`` (the filename
of the file that will be automatically created under source).
We also need to add somewhere in the index or files it references the auto-doc
references for all the classes, otherwise we won't get the relevant docstrings.
We added it as:

.. code-block:: rst

    .. toctree::
       :maxdepth: 2
       :caption: Contents:

       config.rst


    API
    ===

    .. automodule:: config_example
       :members:

in ``index.rst``.

Finally, we run:

.. code-block:: shell

    echo $'Config\n===========' > source/config.rst
    make html
    make html

First we created a mostly empty config.rst file. Otherwise sphinx doesn't
include it when it is generated. Next we ran ``make html`` twice, the first
time it automatically generates the following ``config_prop_docs.yaml`` file:

.. code-block:: yaml

    config_example.App:
      name:
      - Some name.
      - ''
      size:
      - Some filename.
      - ''
    config_example.AppPanel:
      color:
      - Color of the app.
      - ''
    config_example.HomePanel:
      shape:
      - Shape of the home.
      - ''

The second ``make html`` extracts the docstrings from this yaml file and
uses that create ``config.rst`` with the following contents:

.. code-block:: rst

    CONFIG_EXAMPLE Config
    =====================

    The following are the configuration options provided by the app. It can be configured by changing appropriate values in the ``config.yaml`` settings file. The options default to the default value of the classes for each of the options.

    `name`:
     Default value::

      ''

     Some name.

    `size`:
     Default value::

      55

     Some filename.


    home panel
    ----------

    `shape`:
     Default value::

      ''

     Shape of the home.


    app panel
    ---------

    `color`:
     Default value::

      ''

     Color of the app.

This rst is automatically rendered by sphinx to nice html with the rest of the docs and
it looks something like:

----

CONFIG_EXAMPLE Config
=====================

The following are the configuration options provided by the app. It can be configured by changing appropriate values in the ``config.yaml`` settings file. The options default to the default value of the classes for each of the options.

`name`:
 Default value::

  ''

 Some name.

`size`:
 Default value::

  55

 Some filename.


home panel
----------

`shape`:
 Default value::

  ''

 Shape of the home.


app panel
---------

`color`:
 Default value::

  ''

 Color of the app.

----

Class vs instance
-----------------

The configuration examples above save the config from the App *instance*.
One can also use the App *class* to dump the yaml. The major difference is that the
``apply_config_child``, ``get_config_property``, ``apply_config_property``,
and ``post_config_applied`` methods, which are instance methods, are skipped and
not used.

Also, unlike for instances, where it would fail if ``_config_children_`` lists
a child property whose value is None, for the class it will fallback on the type
hint of the property, if one is defined.

Using the ``App`` class, rather than a ``App()`` instance is helpful during doc
building when it may not be possible to instantiate the full App
(see the docs example above that uses the class instance with type hints).

Reusing other project docs
--------------------------

Because we rely on autodoc to generate ``config_prop_docs.yaml``, tree-config
provides a mechanism to reuse the docstrings from other projects we depend on.

E.g. imagine we depend on ``remote1`` and ``remote2`` projects who defines classes
that is configurable and our projects inherits and extends them with further
configurable properties.
Also assume these remote projects dumped their configurable docstrings to
``config_prop_docs.yaml`` like in the example and made it available in the
root of their sphinx generated docs e.g. on github-pages.

Then, tree-config provides tools to merge those docstrings into ours to be able
to create ``config.rst`` from them as follows:

.. code-block:: shell

    echo $'Config\n===========' > source/config.rst
    python -m tree_config.doc_gen download \
        -u "https://user.github.io/remote1/config_prop_docs.yaml" -o config_prop_docs.yaml
    python -m tree_config.doc_gen download -f config_prop_docs.yaml \
        -u "https://matham.github.io/remote2/config_prop_docs.yaml" -o config_prop_docs.yaml
    make html
    make html

This downloads and merges the yaml files from our dependencies, adds to it our own
docs, and generates the ``config.rst``.
