"""
    This file is part of OctoPNP

    OctoPNP is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    OctoPNP is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with OctoPNP.  If not, see <http://www.gnu.org/licenses/>.

    Main author: Florens Wasserfall <wasserfall@kalanka.de>
"""

# coding=utf-8
from __future__ import absolute_import


import octoprint.plugin
import re
from subprocess import call
import os
import time
import base64

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
			"vacnozzle": {
				"x": 0,
				"y": 0,
				"extruder_nr": 2
			},
			"camera": {
				"head": {
					"x": 0,
					"y": 0,
					"z": 0,
					"path": ""
				},
				"bed": {
					"x": 0,
					"y": 0,
					"z": 0,
					"path": ""
				}
			}
		}

	def get_template_configs(self):
		return [
			dict(type="tab", custom_bindings=True),
			dict(type="settings", custom_bindings=True)
		]

	def get_assets(self):
		return dict(
			js=["js/OctoPNP.js"]
		)

	# Use the on_event hook to extract XML data every time a new file has been loaded by the user
	def on_event(self, event, payload):
		#extraxt part informations from inline xmly
		if event == "FileSelected":
			self._currentPart = None
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
				sane, msg = self.smdparts.load(xml)
				if sane:
					self._logger.info("Extracted information on %d parts from gcode file %s", self.smdparts.getPartCount(), payload.get("file"))
					self._updateUI("FILE", "")
				else:
					self._logger.info("XML parsing error: " + msg)
					self._updateUI("ERROR", "XML parsing error: " + msg)
			else:
				#gcode file contains no part information -> clear smdpart object
				self.smdparts.unload()
				self._updateUI("FILE", "")


	"""
	Use the gcode hook to interrupt the printing job on custom M361 commands.
	This hook is designed as some kind of a "state machine". The reason is,
	that we have to circumvent the buffered gcode execution in the printer.
	To take a picture, the buffer must be emptied to ensure that the printer has executed all previous moves
	and is now at the desired position. To achieve this, a M400 command is injected after the
	camera positioning command, followed by a M361. This causes the printer to send the
	next acknowledging ok not until the positioning is finished. Since the next command is a M361,
	octoprint will call the gcode hook again and we are back in the game, iterating to the next state.
	"""
	def hook_gcode(self, comm_obj, cmd):
		if "M361" in cmd:
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
				self._printer.command("M361")
				return "G4 P0" # return dummy command
			if self._state == self.STATE_PLACE:
				self._placePart(self._currentPart)
				self._state = self.STATE_NONE
				return "G4 P0" # return dummy command


	def _moveCameraToPart(self, partnr):
		# move camera to part position
		tray_offset = self._getTrayPosFromPartNr(partnr) # get box position on tray
		camera_offset = [tray_offset[0]-float(self._settings.get(["camera", "head", "x"])), tray_offset[1]-float(self._settings.get(["camera", "head", "y"])), float(self._settings.get(["camera", "head", "z"])) + tray_offset[2]]
		cmd = "G1 X" + str(camera_offset[0]) + " Y" + str(camera_offset[1]) + " Z" + str(camera_offset[2]) + " F" + str(self.FEEDRATE)
		self._logger.info("Move camera to: " + cmd)
		self._printer.command("G1 Z" + str(self._currentZ+5) + " F" + str(self.FEEDRATE)) # lift printhead
		self._printer.command(cmd)


	def _pickPart(self, partnr):
		# wait n seconds to make sure cameras are ready
		time.sleep(1)
		# take picture
		if self._grabImages():
			headPath = os.path.dirname(os.path.realpath(__file__)) + self._settings.get(["camera", "head", "path"])

			#update UI
			self._updateUI("IMAGE", headPath)

			#extract position information
			cm_x,cm_y=self.imgproc.get_displacement(headPath)
		else:
			cm_x=cm_y=0
			self._updateUI("ERROR", "Camera not ready")

		part_offset = [cm_x, cm_y]
		self._logger.info("PART OFFSET:" + str(part_offset))

		tray_offset = self._getTrayPosFromPartNr(partnr)
		vacuum_dest = [tray_offset[0]+part_offset[0]-float(self._settings.get(["vacnozzle", "x"])),\
						 tray_offset[1]+part_offset[1]-float(self._settings.get(["vacnozzle", "y"])),\
						 tray_offset[2]+self.smdparts.getPartHeight(partnr)]

		# move vac nozzle to part and pick
		cmd = "G1 X" + str(vacuum_dest[0]) + " Y" + str(vacuum_dest[1]) + " F" + str(self.FEEDRATE)
		self._printer.command(cmd)
		self._printer.command("G1 Z" + str(vacuum_dest[2]+5))
		self._releaseVacuum()
		self._printer.command("G1 Z" + str(vacuum_dest[2]) + "F1000")
		self._gripVacuum()
		self._printer.command("G4 S1")
		self._printer.command("G1 Z" + str(vacuum_dest[2]+5) + "F1000")

		# move to bed camera
		vacuum_dest = [float(self._settings.get(["camera", "bed", "x"]))-float(self._settings.get(["vacnozzle", "x"])),\
					   float(self._settings.get(["camera", "bed", "y"]))-float(self._settings.get(["vacnozzle", "y"])),\
					   float(self._settings.get(["camera", "bed", "z"]))]

		cmd = "G1 X" + str(vacuum_dest[0]) + " Y" + str(vacuum_dest[1]) + " Z" + str(vacuum_dest[2]) + " F"  + str(self.FEEDRATE)
		self._printer.command(cmd)
		self._logger.info("Moving to bed camera: %s", cmd)


	def _placePart(self, partnr):
		orientation_offset = 0
		displacement = [0, 0]

		# find destination at the object
		destination = self.smdparts.getPartDestination(partnr)

		# take picture
		bedPath = os.path.dirname(os.path.realpath(__file__)) + self._settings.get(["camera", "bed", "path"])
		if self._grabImages():
			#update UI
			self._updateUI("IMAGE", bedPath)

			# get rotation offset
			orientation_offset = self.imgproc.get_orientation(bedPath)
		else:
			self._updateUI("ERROR", "Camera not ready")

		#rotate object
		# switch to vacuum extruder
		self._printer.command("T" + str(self._settings.get(["vacnozzle", "extruder_nr"])))
		self._printer.command("G92 E0")
		self._printer.command("G1 E" + str(destination[3]-orientation_offset) + " F" + str(self.FEEDRATE))

		time.sleep(2)

		# take picture to find part offset
		if self._grabImages():
			#update UI
			self._updateUI("IMAGE", bedPath)

			displacement = self.imgproc.get_centerOfMass(bedPath)
		else:
			self._updateUI("ERROR", "Camera not ready")

		print "displacement - x: " + str(displacement[0]) + " y: " + str(displacement[1])

		# move to destination
		cmd = "G1 X" + str(destination[0]-float(self._settings.get(["vacnozzle", "x"]))) \
			  + " Y" + str(destination[1]-float(self._settings.get(["vacnozzle", "y"]))) \
			  + " Z" + str(destination[2]+self.smdparts.getPartHeight(partnr)+5) + " F" + str(self.FEEDRATE)
		self._logger.info("object destination: " + cmd)
		#self._printer.command(cmd)
		#self._printer.command("G1 Z" + str(destination[2]+self.smdparts.getPartHeight(partnr)))

		#release part
		#self._releaseVacuum()


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
			)
			if self._currentPart: data["part"] = self._currentPart
		elif event is "IMAGE":
			# open image and convert to base64
			f = open(parameter,"r")
			data = dict(
				src = "data:image/" + os.path.splitext(parameter)[1] + ";base64,"+base64.b64encode(bytes(f.read()))
			)

		message = dict(
			event=event,
			data=data
		)
		self._pluginManager.send_plugin_message("OctoPNP", message)