# coding=utf-8
from __future__ import absolute_import


import octoprint.plugin
import re
from subprocess import call
import os
import time

from .SmdParts import SmdParts
from .ImageProcessing import ImageProcessing


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
			octoprint.plugin.SettingsPlugin,
			octoprint.plugin.AssetPlugin):

	STATE_NONE = 0
	STATE_PICK = 1
	STATE_ALIGN = 2
	STATE_PLACE = 3

	FEEDRATE = 4000.000

	smdparts = SmdParts()

	def __init__(self):
		self._state = self.STATE_NONE
		self._currentPart = 0
		self._currentZ = None


	def on_after_startup(self):
		self.imgproc = ImageProcessing(float(self._settings.get(["tray", "boxsize"])))
		#used for communication to UI
		self._pluginManager = octoprint.plugin.plugin_manager()

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
					"offset_z": 0,
					"path": ""
				},
				"bed": {
					"offset_x": 0,
					"offset_y": 0,
					"offset_z": 0
				},
			},
			"vacuum": {
				"offset_x": 0,
				"offset_y": 0,
				"extruder": 2
			}
		}

	def get_template_vars(self):
		return dict(tray_x=self._settings.get(["tray", "x"]))

	def get_template_configs(self):
		return [
			dict(type="tab", custom_bindings=True),
			dict(type="settings", custom_bindings=False)
		]

	def get_assets(self):
		return dict(
			js=["js/OctoPNP.js"]
		)

	def on_event(self, event, payload):
		#extraxt part informations from inline xmly
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

			#Update UI
			self._updateUI("FILE", "")


	def hook_gcode(self, comm_obj, cmd):
		if "M361" in cmd:
			print "hook: " + cmd
			if self._state == self.STATE_NONE:
				self._state = self.STATE_PICK
				if self._printer.getCurrentData()["currentZ"]:
					self._currentZ = float(self._printer.getCurrentData()["currentZ"])
				else:
					self._currentZ = 0.0
				command = re.search("P\d*", cmd).group() #strip the M361
				self._currentPart = int(command[1:])
				self._updateUI("OPERATION", "pick")
				self._moveCameraToPart(self._currentPart)
				self._printer.command("M400")
				self._printer.command("G4 S1")
				self._printer.command("G4 P0")
				self._printer.command("M361")
				return "G4 P0" # return dummy command
			if self._state == self.STATE_PICK:
				self._state = self.STATE_ALIGN
				self._pickPart(self._currentPart)
				self._printer.command("M400")
				self._printer.command("G4 P0")
				self._printer.command("G4 P0")
				self._printer.command("M361")
				return "G4 P0" # return dummy command
			if self._state == self.STATE_ALIGN:
				self._state = self.STATE_PLACE
				print "Align Part"
				self._printer.command("M361")
				return "G4 P0" # return dummy command
			if self._state == self.STATE_PLACE:
				self._placePart(self._currentPart)
				self._state = self.STATE_NONE
				return "G4 P0" # return dummy command


			"""command = re.search("P\d*", cmd.group()).group() #strip the M361
			self.placePart(int(command[1:]))
			return "" #swallow M361 command, useless for printer"""


	def _moveCameraToPart(self, partnr):
		# move camera to part position
		tray_offset = self._getTrayPosFromPartNr(partnr) # get box position on tray
		camera_offset = [tray_offset[0]-float(self._settings.get(["camera", "head", "offset_x"])), tray_offset[1]-float(self._settings.get(["camera", "head", "offset_y"])), float(self._settings.get(["camera", "head", "offset_z"])) + tray_offset[2]]
		cmd = "G1 X" + str(camera_offset[0]) + " Y" + str(camera_offset[1]) + " Z" + str(camera_offset[2]) + " F" + str(self.FEEDRATE)
		print "Move camera to: " + cmd
		self._printer.command("G1 Z" + str(self._currentZ+5) + " F" + str(self.FEEDRATE)) # lift printhead
		self._printer.command(cmd)


	def _pickPart(self, partnr):
		# wait n seconds to make sure cameras are ready
		time.sleep(1)
		print "TAKING PICTURE NOW!!!!!!"
		# take picture
		if self._grabImages():
			#extract position information
			headPath = os.path.dirname(os.path.realpath(__file__)) + self._settings.get(["camera", "head", "path"])
			cm_x,cm_y=self.imgproc.get_displacement(headPath)
		else:
			cm_x=cm_y=0
			self._updateUI("ERROR", "Camera not ready")

		part_offset = [cm_x, cm_y]
		print "PART OFFSET:", part_offset

		tray_offset = self._getTrayPosFromPartNr(partnr)
		vacuum_dest = [tray_offset[0]+part_offset[0]-float(self._settings.get(["vacuum", "offset_x"])),\
						 tray_offset[1]+part_offset[1]-float(self._settings.get(["vacuum", "offset_y"])),\
						 tray_offset[2]+self.smdparts.getPartHeight(partnr)]

		# move vac nozzle to part and pick
		cmd = "G1 X" + str(vacuum_dest[0]) + " Y" + str(vacuum_dest[1]) + " F" + str(self.FEEDRATE)
		self._printer.command(cmd)
		cmd = "G1 Z" + str(vacuum_dest[2]+5)
		self._printer.command(cmd)
		self._releaseVacuum()
		self._printer.command("G1 Z" + str(vacuum_dest[2]) + "F1000")
		self._gripVacuum()
		self._printer.command("G4 S1")
		self._printer.command("G1 Z" + str(vacuum_dest[2]+5) + "F1000")

		# move to bed camera
		vacuum_dest = [float(self._settings.get(["camera", "bed", "offset_x"]))-float(self._settings.get(["vacuum", "offset_x"])),\
					   float(self._settings.get(["camera", "bed", "offset_y"]))-float(self._settings.get(["vacuum", "offset_y"])),\
					   float(self._settings.get(["camera", "bed", "offset_z"]))]

		cmd = "G1 X" + str(vacuum_dest[0]) + " Y" + str(vacuum_dest[1]) + " Z" + str(vacuum_dest[2]) + " F"  + str(self.FEEDRATE)
		self._printer.command(cmd)
		print self._logger.info("Moving to bed camera: %s", cmd)


	def _placePart(self, partnr):
		# take picture
		if self._grabImages():
			pass
			#extract position information
			#cm_x,cm_y=self.imgproc.get_cm()
		else:
			self._updateUI("ERROR", "Camera not ready")


		# rotate object, compute offset

		# find destination at the object
		destination = self.smdparts.getPartDestination(partnr)
		#rotate object
		if destination[2] != 0:
			# switch to vacuum extruder
			self._printer.command("T" + self._settings.get(["vacuum", "extruder"]))
			self._printer.command("G92 E0")
			self._printer.command("G1 E" + str(destination[2]) + " F" + str(self.FEEDRATE))

		# move to destination
		cmd = "G1 X" + str(destination[0]-float(self._settings.get(["vacuum", "offset_x"]))) \
			  + " Y" + str(destination[1]-float(self._settings.get(["vacuum", "offset_y"]))) \
			  + " Z" + str(self._currentZ+self.smdparts.getPartHeight(partnr)+5) + " F"  + str(self.FEEDRATE)
		print "object destination: " + cmd
		self._printer.command(cmd)
		self._printer.command("G1 Z" + str(self._currentZ+self.smdparts.getPartHeight(partnr)))

		#release part
		self._releaseVacuum()


	# get the position of the box (center of the box) containing part x relative to the [0,0] corner of the tray
	def _getTrayPosFromPartNr(self, partnr):
		partPos = self.smdparts.getPartPosition(partnr)
		row = (partPos-1)/int(self._settings.get(["tray", "columns"]))+1
		col = ((partPos-1)%int(self._settings.get(["tray", "columns"])))+1
		self._logger.info("Selected object: %d. Position: box %d, row %d, col %d", partnr, partPos, row, col)

		boxsize = float(self._settings.get(["tray", "boxsize"]))
		rimsize = float(self._settings.get(["tray", "rimsize"]))
		x = (col-1)*boxsize + boxsize/2 + col*rimsize + float(self._settings.get(["tray", "x"]))
		y = (row-1)*boxsize + boxsize/2 + row*rimsize + float(self._settings.get(["tray", "y"]))
		return [x, y, float(self._settings.get(["tray", "z"]))]

	def _gripVacuum(self):
		self._printer.command("M400")
		self._printer.command("M400")
		self._printer.command("G4 S1")
		self._printer.command("M340 P0 S1500")
		self._printer.command("G4 S1")

	def _releaseVacuum(self):
		self._printer.command("M400")
		self._printer.command("M400")
		self._printer.command("G4 S1")
		self._printer.command("M340 P0 S1200")
		self._printer.command("G4 S1")

	def _grabImages(self):
		result = True
		grabScript = os.path.dirname(os.path.realpath(__file__)) + "/cameras/grab.sh"
		if call([grabScript]) != 0:
			self._logger.info("ERROR: camera not ready!")
			result = False
		return result


	def _updateUI(self, event, parameter):
		data = dict(
			info="dummy"
		)
		if event == "FILE":
			if self.smdparts.isFileLoaded():
				data = dict(
					parts=self.smdparts.getPartCount()
				)
		elif event == "OPERATION":
			data = dict(
				type = parameter,
				part = self._currentPart
			)
		elif event == "ERROR":
			data = dict(
				type = parameter,
				part = self._currentPart
			)
		elif event is "IMAGE":
			data = dict(
				src = parameter
			)

		message = dict(
			event=event,
			data=data
		)
		self._pluginManager.send_plugin_message("OctoPNP", message)