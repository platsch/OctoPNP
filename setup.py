# coding=utf-8
import setuptools

########################################################################################################################

# The plugin's identifier, has to be unique
plugin_identifier = "OctoPNP"

# The plugin's python package, should be "octoprint_<plugin identifier>", has to be unique
plugin_package = "octoprint_%s" % plugin_identifier

# The plugin's human readable name. Can be overwritten within OctoPrint's internal data via __plugin_name__ in the
# plugin module
plugin_name = "OctoPNP"

# The plugin's version. Can be overwritten within OctoPrint's internal data via __plugin_version__ in the plugin module
plugin_version = "0.2"

# The plugin's description. Can be overwritten within OctoPrint's internal data via __plugin_description__ in the plugin
# module
plugin_description = "OctoPrint plugin for camera based pick 'n place control"

# The plugin's author. Can be overwritten within OctoPrint's internal data via __plugin_author__ in the plugin module
plugin_author = "Florens Wasserfall"

# The plugin's author's mail address.
plugin_author_email = "wasserfall@kalanka.de"

# The plugin's homepage URL. Can be overwritten within OctoPrint's internal data via __plugin_url__ in the plugin module
plugin_url = "https://github.com/platsch/OctoPNP"

# The plugin's license. Can be overwritten within OctoPrint's internal data via __plugin_license__ in the plugin module
plugin_license = "AGPLv3"

# Additional package data to install for this plugin. The subfolders "templates", "static" and "translations" will
# already be installed automatically if they exist.
plugin_additional_data = []

########################################################################################################################


def package_data_dirs(source, sub_folders):
    import os

    dirs = []

    for d in sub_folders:
        folder = os.path.join(source, d)
        if not os.path.exists(folder):
            continue

        for dirname, _, files in os.walk(folder):
            dirname = os.path.relpath(dirname, source)
            for f in files:
                dirs.append(os.path.join(dirname, f))

    return dirs


def params():
    # Our metadata, as defined above
    name = plugin_name
    version = plugin_version
    description = plugin_description
    author = plugin_author
    author_email = plugin_author_email
    url = plugin_url
    license = plugin_license

    # we only have our plugin package to install
    packages = [plugin_package]

    # we might have additional data files in sub folders that need to be installed too
    package_data = {
        plugin_package: package_data_dirs(
            plugin_package,
            ["static", "templates", "translations", "cameras"] + plugin_additional_data,
        )
    }
    include_package_data = True

    # If you have any package data that needs to be accessible on the file system, such as templates or static assets
    # this plugin is not zip_safe.
    zip_safe = False

    # Read the requirements from our requirements.txt file
    install_requires = open("requirements.txt").read().split("\n")

    # Hook the plugin into the "octoprint.plugin" entry point, mapping the plugin_identifier to the plugin_package.
    # That way OctoPrint will be able to find the plugin and load it.
    entry_points = {
        "octoprint.plugin": ["%s = %s" % (plugin_identifier, plugin_package)]
    }

    return locals()


setuptools.setup(**params())
