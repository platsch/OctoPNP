# coding=utf-8
from __future__ import absolute_import


import octoprint.plugin

class OctoPNP(octoprint.plugin.StartupPlugin,
			  octoprint.plugin.TemplatePlugin,
			  octoprint.plugin.EventHandlerPlugin,
			  octoprint.plugin.SettingsPlugin):

	def on_after_startup(self):
		self._logger.info("Hello World! setting: %s" % self._settings.get(["tray_x"]))
		print self._settings.get(["tray_x"])

	def get_settings_defaults(self):
		return dict(tray_x="teststring")

	def get_template_vars(self):
		return dict(tray_x=self._settings.get(["tray_x"]))


	def on_event(self, event, payload):
		self._logger.info("Event: " + event)
		if event == "PrintPaused":
			self._logger.info("send command: G1 X0 F5000")
			self._printer.command("G1 X0 F5000")

	def get_template_configs(self):
		return [
			dict(type="tab", custom_bindings=False),
			dict(type="settings", custom_bindings=False)
			#dict(type="tab", data_bind="stateString: teststring")
		]

# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "OctoPNP"
__plugin_implementations__ = [OctoPNP()]
