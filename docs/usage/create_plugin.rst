===============
Create a Plugin
===============


Plugin Class
------------

To create a plugin that is able to connect to another service you have to first create a plugin class.
This custom plugin class needs to inherit from :code:`kitovu.sync.syncplugin.AbstractSyncPlugin`.

This example illustrates all required methods::

 from kitovu.sync import syncplugin

 class ExamplePlugin(syncplugin.AbstractSyncPlugin):
     """A plugin that handles connections with an example service"""

     def connect(self, url: str, options: typing.Dict[str, typing.Any]) -> None:
         """Setup the connection to your service.

         Keyword arguments:
         url -- the url to connect to
         options -- a dictionary containing all configuration from the configuration file
         """
         pass

     def disconnect(self) -> None:
         """Disconnects from your service"""
         pass

     def create_local_digest(self, path: pathlib.Path) -> str:
         """Returns the digest for the local file.

         Keyword arguments:
         path -- the local path of the file to create the digest for
         """
         pass

     def create_remote_digest(self, path: pathlib.PurePath) -> str:
         """Returns the digest for the remote file.

         Keyword arguments:
         path -- the remote path of the file to create the digest for
         """
         pass

     def list_path(self, path: pathlib.PurePath) -> typing.Iterable[pathlib.PurePath]:
         """List all files within the passed directory.

         Keyword arguments:
         path -- the remote path of the directory from which to show all files
         """
         pass

     def retrieve_file(self, path: pathlib.PurePath, fileobj: typing.IO[bytes]) -> None:
         """Retrieve the file at the specified path and write it to the passed file object.

         Keyword arguments:
         path -- the remote path of the file to retrieve
         fileobj -- the IO object of the local file to write to
         """
         pass
