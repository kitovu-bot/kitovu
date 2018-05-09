===============
Create a Plugin
===============

Plugin Class
------------

Implementation
~~~~~~~~~~~~~~

To create a plugin that is able to connect to another service you have to first create a plugin class.
This custom plugin class needs to inherit from :class:`kitovu.sync.syncplugin.AbstractSyncPlugin`.

For an example implementation see :mod:`kitovu.sync.plugin.smb`.

Registration
~~~~~~~~~~~~

The plugin class needs to be registered with stevedore_.

You need to create a `setup.py` file like this::

 from setuptools import setup

 setup(
     # other setup parameters

     entry_points={
         'kitovu.sync.plugin': [
             'my-example = my.plugin:ExamplePlugin',
         ],
     },

     # other setup parameters
 )

By setting :code:`entry_points` you can list all plugins you implement in this package.

`my-example`
  This is the name of the plugin used in the kitovu configuration.
`my.plugin:ExamplePlugin`
  This is the namespace and class of the plugin to use.

For further information see the stevedore documentation for `creating a plugin`_.

.. _stevedore: https://docs.openstack.org/stevedore/latest/
.. _`creating a plugin`: https://docs.openstack.org/stevedore/latest/user/tutorial/creating_plugins.html

User Output
------------

Errors
~~~~~~

If there occurs an error which should cancel the entire execution of the plugin you can throw a :class:`kitovu.utils.UsageError`.
The command line tool or the user interface will print those messages.

This is used for example if the server rejects a request or is not available.

Any other exception will lead to the kitovu application to terminate.

Warnings
~~~~~~~~

To print warnings to the user without aborting the current operation, use Python's `logging framework`_.
It's recommended to use ``logger = logging.getLogger(__name__)`` to get an unique logger for your plugin.

.. _logging framework: https://docs.python.org/3/library/logging.html
