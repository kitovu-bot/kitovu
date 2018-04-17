===============
Create a Plugin
===============

Plugin Class
------------

Implementation
~~~~~~~~~~~~~~

To create a plugin that is able to connect to another service you have to first create a plugin class.
This custom plugin class needs to inherit from :code:`kitovu.sync.syncplugin.AbstractSyncPlugin`.

For an example implementation see :code:`kitovu.sync.plugin.smb`.

Registration
~~~~~~~~~~~~

The plugin class needs to be registered with stevedore_.

You need to create a `setup.py` file like this::

 from setuptools import setup, find_packages

 setup(
     name='my-example-plugin',
     version='1.0',

     description='An example for a kitovu plugin',

     author='Your Name',
     author_email='your.name@example.com',

     url='http://example.com/your/url',

     classifiers=['Development Status :: 3 - Alpha',
                  'License :: OSI Approved :: Apache Software License',
                  'Programming Language :: Python',
                  'Programming Language :: Python :: 2',
                  'Programming Language :: Python :: 2.7',
                  'Programming Language :: Python :: 3',
                  'Programming Language :: Python :: 3.4',
                  'Intended Audience :: Developers',
                  'Environment :: Console',
                  ],

     platforms=['Any'],

     scripts=[],

     provides=['kitovu.sync.plugin'],

     packages=find_packages(),
     include_package_data=True,

     entry_points={
         'kitovu.sync.plugin': [
             'my-example = my.plugin:ExamplePlugin',
         ],
     },

     zip_safe=False,
 )

The important key is :code:`entry_points`.
There you can list all plugins you implement.

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

If there occurs an error which should cancel the entire execution of the plugin you can throw a :code:`kitovu.utils.UsageError`.
The command line tool or the user interface will print those messages.

This is used for example if the server rejects a request or is not available.

Any other exception will lead to the kitovu application to terminate.

Warnings
~~~~~~~~

.. FIXME

If there occurs something that the user should be informed about, but other files can still be synced, you can *[TBD]*

This is used for example if a file disapeard between listing all files and retrieving a file.
