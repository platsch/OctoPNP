# coding=utf-8
from __future__ import absolute_import


import octoprint.plugin
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

	STATE_NONE = 0
	STATE_PICK = 1
	STATE_ALIGN = 2
	STATE_PLACE = 3

	smdparts = SmdParts()

	def __init__(self):
		self._state = self.STATE_NONE
		self._currentPart = 0
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
				"rimsize": 1.0,
			},
			"camera": {
				"head": {
					"offset_x": 0,
					"offset_y": 0,
					"offset_z": 0
				},
				"bed": {
					"offset_x": 0,
					"offset_y": 0,
					"offset_z": 0
				},
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


	def get_template_configs(self):
		return [
			dict(type="tab", custom_bindings=False),
			dict(type="settings", custom_bindings=False)
		]

	def hook_gcode(self, comm_obj, cmd):
		if "M361" in cmd:
			print "hook: " + cmd
			if self._state == self.STATE_NONE:
				self._state = self.STATE_PICK
				command = re.search("P\d*", cmd).group() #strip the M361
				self._currentPart = int(command[1:])
				self._moveCameraToPart(self._currentPart)
				self._printer.command("M400")
				self._printer.command("G4 P0")
				self._printer.command("G4 P0")
				self._printer.command("M361")
				return "G4 P0" # return dummy command
			if self._state == self.STATE_PICK:
				self._state = self.STATE_ALIGN
				self._pickPart(self._currentPart)
				self._printer.command("M361")
				return "G4 P0" # return dummy command
			if self._state == self.STATE_ALIGN:
				self._state = self.STATE_PLACE
				print "Align Part"
				self._printer.command("M361")
				return "G4 P0" # return dummy command
			if self._state == self.STATE_PLACE:
				print "Place Part"
				self._state = self.STATE_NONE
				return "G4 P0" # return dummy command


			"""command = re.search("P\d*", cmd.group()).group() #strip the M361
			self.placePart(int(command[1:]))
			return "" #swallow M361 command, useless for printer"""


	# executes the movements to find, pick and place a certain part
	def _moveCameraToPart(self, partnr):
		# move camera to part position
		tray_offset = self._getTrayPosFromPartNr(partnr) # get box position on tray
		camera_offset = [tray_offset[0]-float(self._settings.get(["camera", "head", "offset_x"])), tray_offset[1]-float(self._settings.get(["camera", "head", "offset_y"])), float(self._settings.get(["camera", "head", "offset_z"])) + tray_offset[2]]
		cmd = "G1 X" + str(camera_offset[0]) + " Y" + str(camera_offset[1]) + " Z" + str(camera_offset[2]) + " F4000"
		print cmd
		self._printer.command(cmd)


	def _pickPart(self, partnr):
		print "TAKING PICTURE NOW!!!!!!"
		self._printer.command("G4 S10")

		# take picture, extract position information
		part_offset = [0, 0]

		tray_offset = self._getTrayPosFromPartNr(partnr)
		vacuum_offset = [tray_offset[0]+part_offset[0]-float(self._settings.get(["vacuum", "offset_x"])),\
						 tray_offset[1]+part_offset[1]-float(self._settings.get(["vacuum", "offset_y"])),\
						 tray_offset[2]+self.smdparts.getPartHeight(partnr)]

		# move vac nozzle to part and pick
		cmd = "G1 X" + str(vacuum_offset[0]) + " Y" + str(vacuum_offset[1]) + " Z" + str(vacuum_offset[2]+5) + " F4000"
		self._printer.command(cmd)
		self._printer.command("M340 P0 S1200")
		self._printer.command("G1 Z" + str(vacuum_offset[2]) + "F500")
		self._printer.command("M340 P0 S1500")
		self._printer.command("G4 S1")
		self._printer.command("G1 Z" + str(vacuum_offset[2]+5) + "F500")

		# move to bed camera

		# take picture, extract position information

		# rotate object, compute offset

		# move to destination at the object

		#release

	# get the position of the box (center of the box) containing part x relative to the [0,0] corner of the tray
	def _getTrayPosFromPartNr(self, partnr):
		partPos = self.smdparts.getPartPosition(partnr)
		row = (partPos+1)/int(self._settings.get(["tray", "columns"]))+1
		col = ((partPos-1)%int(self._settings.get(["tray", "columns"])))+1
		self._logger.info("Selected object: %d. Position: box %d, row %d, col %d", partnr, partPos, row, col)

		boxsize = float(self._settings.get(["tray", "boxsize"]))
		rimsize = float(self._settings.get(["tray", "rimsize"]))
		x = (col-1)*boxsize + boxsize/2 + col*rimsize + float(self._settings.get(["tray", "x"]))
		y = (row-1)*boxsize + boxsize/2 + row*rimsize + float(self._settings.get(["tray", "y"]))
		return [x, y, float(self._settings.get(["tray", "z"]))]