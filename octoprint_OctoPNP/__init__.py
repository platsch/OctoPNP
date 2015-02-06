# coding=utf-8
from __future__ import absolute_import


import octoprint.plugin
import time
import re
from .SmdParts import SmdParts


class OctoPNP(octoprint.plugin.StartupPlugin,
			  octoprint.plugin.TemplatePlugin,
			  octoprint.plugin.EventHandlerPlugin,
			  octoprint.plugin.SettingsPlugin):

	smdparts = SmdParts()

	def __init__(self):
		pass


	def on_after_startup(self):
		#self._logger.info("Hello World! setting: %s" % self._settings.get(["tray_x"]))
		#print self._settings.get(["tray_x"])
		pass

	def get_settings_defaults(self):
		return dict(tray_x="teststring")

	def get_template_vars(self):
		return dict(tray_x=self._settings.get(["tray_x"]))


	def on_event(self, event, payload):
		if event == "FileSelected":
			self._logger.info("file: " + payload.get("file"))
			xml = "";
			f = open(payload.get("file"), 'r')
			for line in f:
				expression = re.search("<.*>", line)
				if expression:
					xml += expression.group() + "\n"
					print expression.group()
			if xml:
				#check for root node existance
				if not re.search("<object.*>", xml.splitlines()[0]):
					xml = "<object name=\"defaultpart\">\n" + xml + "\n</object>"

				#parse xml data
				self.smdparts.load(xml)

				print self.smdparts.getPartPosition(3)
			else:
				self.smdparts.unload()

		#	self._printer.command("G1 X0 F5000")


	def get_template_configs(self):
		return [
			dict(type="tab", custom_bindings=False),
			dict(type="settings", custom_bindings=False)
			#dict(type="tab", data_bind="stateString: teststring")
		]

	def placePart(self, partnr):
		print "placing part nr " + str(partnr) + " which is at position " + str(self.smdparts.getPartPosition(3))




def hook_gcode(comm_obj, cmd):
	command = re.search("M361\s*P\d*", cmd)
	if command:
		print "hook, command: " + command.group()
		command = re.search("P\d*", command.group()).group() #strip the M361
		opnp = OctoPNP()
		opnp.placePart(int(command[1:]))

	#t=OctoPNP()
	#t.testprint()
	"""if cmd == "G92 E0":
		print "sleep"
#		self._printer.command("M1234 P0")
		#opnp.testprint()
		time.sleep(10)
		comm_obj._doSend("M1234 P0")
		print "send M1234"
		time.sleep(10)
		return "M4321"
		"""

# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "OctoPNP"
__plugin_hooks__ = {'octoprint.comm.protocol.gcode': hook_gcode}
__plugin_implementations__ = [OctoPNP()]