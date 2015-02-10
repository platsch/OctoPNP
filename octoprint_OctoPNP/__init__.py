# coding=utf-8
from __future__ import absolute_import


import octoprint.plugin
import time
import re
from .SmdParts import SmdParts


__plugin_name__ = "OctoPNP"

#instantiate plugin object and register hook for gcode injection
def __plugin_init__():

	octopnp = OctoPNP()

	global __plugin_implementations__
	__plugin_implementations__ = [octopnp]

	global __plugin_hooks__
	__plugin_hooks__ = {'octoprint.comm.protocol.gcode': octopnp.hook_gcode}


class OctoPNP(octoprint.plugin.StartupPlugin,
			  octoprint.plugin.TemplatePlugin,
			  octoprint.plugin.EventHandlerPlugin,
			  octoprint.plugin.SettingsPlugin):

	smdparts = SmdParts()

	def __init__(self):
		pass


	def on_after_startup(self):
		pass

	def get_settings_defaults(self):
		return dict(tray_x="teststring")

	def get_template_vars(self):
		return dict(tray_x=self._settings.get(["tray_x"]))


	def on_event(self, event, payload):
		#extraxt part informations from inline xml
		if event == "FileSelected":
			xml = "";
			f = open(payload.get("file"), 'r')
			for line in f:
				expression = re.search("<.*>", line)
				if expression:
					xml += expression.group() + "\n"
			if xml:
				#check for root node existence
				if not re.search("<object.*>", xml.splitlines()[0]):
					xml = "<object name=\"defaultpart\">\n" + xml + "\n</object>"

				#parse xml data
				self.smdparts.load(xml)
				self._logger.info("Extracted information on %d parts from gcode file %s", self.smdparts.getPartCount(), payload.get("file"))
			else:
				#gcode file contains no part information -> clear smdpart object
				self.smdparts.unload()

		#	self._printer.command("G1 X0 F5000")


	def get_template_configs(self):
		return [
			dict(type="tab", custom_bindings=False),
			dict(type="settings", custom_bindings=False)
		]

	def hook_gcode(self, comm_obj, cmd):
		command = re.search("M361\s*P\d*", cmd)
		if command:
			command = re.search("P\d*", command.group()).group() #strip the M361
			self.placePart(int(command[1:]))
			return "" #swallow M361 command, useless for printer

	# executes the movements to find, pick and place a certain part
	def placePart(self, partnr):
		# move camera to part position
		xval = self._settings.get(["tray_x"])
		tray_offset = self._getTrayPosFromPartNr(partnr)
		#self._printer.command("")

	# get the position of the box containing part x relative to the [0,0] corner of the tray
	def _getTrayPosFromPartNr(self, partnr):
		partPos = self.smdparts.getPartPosition(partnr)
		row = partPos/int(self._settings.get(["tray_rows"]))+1
		col = partPos%int(self._settings.get(["tray_rows"]))
		self._logger.info("Selected object: %d. Position: box %d, row %d, col %d", partnr, partPos, row, col)

		boxsize = int(self._settings.get(["tray_boxsize"]))
		rimsize = int(self._settings.get(["tray_rimsize"]))
		x = (col-1)*boxsize + float(boxsize)/2 + col*rimsize
		y = (row-1)*boxsize + float(boxsize)/2 + row*rimsize
		return [x, y]