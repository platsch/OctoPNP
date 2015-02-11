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
		return {
			#"publicHost": None,
			#"publicPort": None,
			"tray": {
				"x": 0,
				"y": 0,
				"z": 0,
				"rows" : 5,
				"columns": 5,
				"boxsize": 10,
				"rimsize": 1.0
			},
			"camera": {
				"offset_x": 0,
				"offset_y": 0,
				"offset_z": 0
			},
			"vacuum": {
				"offset_x": 0,
				"offset_y": 0
			}
		}

	def get_template_vars(self):
		return dict(tray_x=self._settings.get(["tray", "x"]))


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
		tray_offset = self._getTrayPosFromPartNr(partnr) # get box position on tray
		tray_offset[0] += float(self._settings.get(["tray", "x"])) # get tray position on printbed
		tray_offset[1] += float(self._settings.get(["tray", "y"]))
		camera_offset = [tray_offset[0]-float(self._settings.get(["camera", "offset_x"])), tray_offset[1]-float(self._settings.get(["camera", "offset_y"])), float(self._settings.get(["camera", "offset_z"])) + float(self._settings.get(["tray", "z"]))]
		cmd = "G1 X" + str(camera_offset[0]) + " Y" + str(camera_offset[1]) + " Z" + str(camera_offset[2]) + " F4000"
		print cmd
		#self._printer.command(cmd)

		# take picture, extract position information

		# move vac nozzle to part and pick

		# move to bed camera

		# take picture, extract position information

		# rotate object, compute offset

		# move to destination at the object

		#release

	# get the position of the box containing part x relative to the [0,0] corner of the tray
	def _getTrayPosFromPartNr(self, partnr):
		partPos = self.smdparts.getPartPosition(partnr)
		row = partPos/int(self._settings.get(["tray", "rows"]))+1
		col = partPos%int(self._settings.get(["tray", "rows"]))
		self._logger.info("Selected object: %d. Position: box %d, row %d, col %d", partnr, partPos, row, col)

		boxsize = float(self._settings.get(["tray", "boxsize"]))
		rimsize = float(self._settings.get(["tray", "rimsize"]))
		x = (col-1)*boxsize + boxsize/2 + col*rimsize
		y = (row-1)*boxsize + boxsize/2 + row*rimsize
		return [x, y]