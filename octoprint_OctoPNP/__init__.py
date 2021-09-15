# -*- coding: utf-8 -*-
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

from __future__ import absolute_import, division, print_function, unicode_literals


import octoprint.plugin
import flask
import json
import re
from subprocess import call
import os
import time
import datetime
import base64
import shutil

from .SmdParts import SmdParts
from .ImageProcessing import ImageProcessing


__plugin_name__ = "OctoPNP"
__plugin_pythoncompat__ = ">=2.7,<4"

#instantiate plugin object and register hook for gcode injection
def __plugin_load__():

    octopnp = OctoPNP()

    global __plugin_implementation__
    __plugin_implementation__ = octopnp

    global __plugin_hooks__
    __plugin_hooks__ = {'octoprint.comm.protocol.gcode.sending': octopnp.hook_gcode_sending, 'octoprint.comm.protocol.gcode.queuing': octopnp.hook_gcode_queuing}

    global __plugin_helpers__
    __plugin_helpers__ = dict(
        get_head_camera_pxPerMM = octopnp._helper_get_head_camera_pxPerMM,
        get_head_camera_image   = octopnp._helper_get_head_camera_image_xy # parameter: [x, y, callback, adjust_focus=True]
    )


class OctoPNP(octoprint.plugin.StartupPlugin,
            octoprint.plugin.TemplatePlugin,
            octoprint.plugin.EventHandlerPlugin,
            octoprint.plugin.SettingsPlugin,
            octoprint.plugin.AssetPlugin,
            octoprint.plugin.SimpleApiPlugin,
            octoprint.plugin.BlueprintPlugin):

    STATE_NONE     = 0
    STATE_PICK     = 1
    STATE_ALIGN    = 2
    STATE_PLACE    = 3
    STATE_EXTERNAL = 9 # used if helper functions are called by external plugins

    FEEDRATE = 4000.000

    smdparts = SmdParts()

    def __init__(self):
        self._state = self.STATE_NONE
        self._currentPart = 0
        self._helper_was_paused = False

        # store callback to send result of an image capture request back to caller
        self._helper_callback = None

    def on_after_startup(self):
        self.imgproc = ImageProcessing(float(self._settings.get(["tray", "box", "boxsize"])), int(self._settings.get(["camera", "bed", "binary_thresh"])), int(self._settings.get(["camera", "head", "binary_thresh"])))
        #used for communication to UI
        self._pluginManager = octoprint.plugin.plugin_manager()

    def get_settings_defaults(self):
        return {
            "tray": {
                # general settings applying to all tray types
                "x": 0,
                "y": 0,
                "z": 0,
                "axis": "Z",
                "type": "BOX", # possible alternatives: FEEDER
                # type specific settings
                "box": {
                    "rows": 5,
                    "columns": 5,
                    "boxsize": 10,
                    "rimsize": 1.0,
                },
                "feeder": {
                    "row_clearance": 3.0,
                    "feederconfiguration": [ {"width": 8.0, "spacing": 5.0, "rotation": 0},  {"width": 12.0, "spacing": 8.0, "rotation": 90} ]
                },
            },
            "vacnozzle": {
                "use_offsets": False,
                "x": 0,
                "y": 0,
                "z_pressure": 0,
                "tool_nr": 2,
                "grip_vacuum_gcode": "M340 P0 S1200",
                "release_vacuum_gcode": "M340 P0 S1500",
                "lower_nozzle_gcode": "",
                "lift_nozzle_gcode": ""
            },
            "camera": {
                "head": {
                    "x": 0,
                    "y": 0,
                    "z": 0,
                    "tool_nr": 0,
                    "pxPerMM": {
                        "x": 50.0,
                        "y": 50.0
                    },
                    "enable_LED_gcode": "",
                    "disable_LED_gcode": "",
                    "path": "",
                    "binary_thresh": 150,
                    "grab_script_path": "",
                    "http_path" : ""
                },
                "bed": {
                    "x": 0,
                    "y": 0,
                    "z": 0,
                    "focus_axis" : "Z",
                    "pxPerMM": {
                        "x": 50.0,
                        "y": 50.0
                    },
                    "enable_LED_gcode": "",
                    "disable_LED_gcode": "",
                    "path": "",
                    "binary_thresh": 150,
                    "grab_script_path": "",
                    "http_path" : ""
                },
                "image_logging": False
            },
            "calibration": {
                "toolchange_gcode": "G1 X100 Y150 F3000"
            },
        }

    def get_template_configs(self):
        return [
            dict(type="tab", template="OctoPNP_tab.jinja2", custom_bindings=True),
            dict(type="settings", template="OctoPNP_settings.jinja2", custom_bindings=True)
            #dict(type="settings", custom_bindings=True)
        ]

    def get_assets(self):
        return dict(
            js=["js/OctoPNP.js",
                "js/settings.js",
                "js/boxTray.js",
                "js/feederTray.js",
                "js/trayUtil.js"]
        )

    # Flask endpoint for the GUI to request camera images. Possible request parameters are "BED" and "HEAD".
    @octoprint.plugin.BlueprintPlugin.route("/camera_image", methods=["GET"])
    def getCameraImage(self):
        result = ""
        if "imagetype" in flask.request.values:
            camera = flask.request.values["imagetype"]
            if ((camera == "HEAD") or (camera == "BED")):
                if self._grabImages(camera):
                    imagePath = self._settings.get(["camera", camera.lower(), "path"])
                    try:
                        f = open(imagePath,"rb")
                        result = flask.jsonify(src="data:image/" + os.path.splitext(imagePath)[1] + ";base64,"+str(base64.b64encode(bytes(f.read())), "utf-8"))
                    except IOError:
                        result = flask.jsonify(error="Unable to open Image after fetching. Image path: " + imagePath)
                else:
                    result = flask.jsonify(error="Unable to fetch image. Check octoprint log for details.")
        return flask.make_response(result, 200)


    # Flask endpoint for the GUI to update component tray assignments
    @octoprint.plugin.BlueprintPlugin.route("/tray_assignments", methods=["GET"])
    def updateTrayAssignments(self):
        if "mapping" in flask.request.values:
            mapping = flask.request.values["mapping"]
            mapping = json.loads(mapping)
            for part in mapping:
                self.smdparts.setPartPosition(int(part), int(mapping[part]["row"]), int(mapping[part]["col"]))
        return flask.make_response("", 200)

    # Use the on_event hook to extract XML data every time a new file has been loaded by the user
    def on_event(self, event, payload):
        #extraxt part informations from inline xmly
        if event == "FileSelected":
            self._currentPart = None
            xml = ""
            gcode_path = self._file_manager.path_on_disk(payload.get("origin"), payload.get("path"))
            f = open(gcode_path, 'r')
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
                    #TODO: validate part informations against tray
                    self._logger.info("Extracted information on %d parts from gcode file %s", self.smdparts.getPartCount(), payload.get("name"))
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
    """
    def hook_gcode_queuing(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if "M361" in cmd:
            if self._state == self.STATE_NONE:
                self._state = self.STATE_PICK
                command = re.search("P\d*", cmd).group() #strip the M361
                self._currentPart = int(command[1:])

                self._logger.info( "Received M361 command to place part: " + str(self._currentPart))

                # pause running printjob to prevent octoprint from sending new commands from the gcode file during the interactive PnP process
                if self._printer.is_printing() or self._printer.is_resuming():
                    self._printer.pause_print()

                self._updateUI("OPERATION", "pick")

                if(self._settings.get(["tray", "type"]) == "BOX"):
                    # enable head camera LEDs
                    if(len(self._settings.get(["camera", "head", "enable_LED_gcode"])) > 0):
                        self._printer.commands(self._settings.get(["camera", "head", "enable_LED_gcode"]))
                    self._logger.info( "Move camera to part: " + str(self._currentPart))
                    self._moveCameraToPart(self._currentPart)

                self._printer.commands("M400")
                self._printer.commands("G4 P1")
                self._printer.commands("M400")
                for i in range(10):
                    self._printer.commands("G4 P1")

                self._printer.commands("M362 OctoPNP")


                return (None,) # suppress command
            else:
                self._logger.info( "ERROR, received M361 command while placing part: " + str(self._currentPart))

    """
    This hook is designed as some kind of a "state machine". The reason is,
    that we have to circumvent the buffered gcode execution in the printer.
    To take a picture, the buffer must be emptied to ensure that the printer has executed all previous moves
    and is now at the desired position. To achieve this, a M400 command is injected after the
    camera positioning command, followed by a M362. This causes the printer to send the
    next acknowledging ok not until the positioning is finished. Since the next command is a M362,
    octoprint will call the gcode hook again and we are back in the game, iterating to the next state.
    Since both, Octoprint and the printer firmware are using a queue, we inject some "G4 P1" commands
    as a "clearance buffer". Those commands simply cause the printer to wait for a millisecond.
    """

    def hook_gcode_sending(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if "M362 OctoPNP" in cmd:
            if self._state == self.STATE_PICK:
                self._state = self.STATE_ALIGN
                self._logger.info("Pick part " + str(self._currentPart))

                # generate new imageProcessing object with updated settings
                self.imgproc = ImageProcessing(float(self._settings.get(["tray", "box", "boxsize"])), int(self._settings.get(["camera", "bed", "binary_thresh"])), int(self._settings.get(["camera", "head", "binary_thresh"])))

                self._pickPart(self._currentPart)
                self._printer.commands("M400")
                self._printer.commands("G4 P1")
                self._printer.commands("M400")

                for i in range(10):
                    self._printer.commands("G4 P1")

                self._printer.commands("M362 OctoPNP")

                return (None,) # suppress command

            if self._state == self.STATE_ALIGN:
                self._state = self.STATE_PLACE
                self._logger.info("Align part " + str(self._currentPart))

                self._alignPart(self._currentPart)
                self._printer.commands("M400")
                self._printer.commands("G4 P1")
                self._printer.commands("M400")

                # still having trouble with images taken before alignment was fully executed...
                self._printer.commands("G4 S2")

                for i in range(10):
                    self._printer.commands("G4 P1")

                self._printer.commands("M362 OctoPNP")

                return (None,) # suppress command

            if self._state == self.STATE_PLACE:
                self._logger.info("Place part " + str(self._currentPart))

                self._placePart(self._currentPart)
                self._printer.commands("M400")
                self._printer.commands("G4 P1")
                self._printer.commands("M400")

                for i in range(10):
                    self._printer.commands("G4 P1")

                self._logger.info("Finished placing part " + str(self._currentPart))
                self._state = self.STATE_NONE

                # resume paused printjob into normal operation
                if self._printer.is_paused() or self._printer.is_pausing():
                    self._printer.resume_print()

                return (None,) # suppress command

        # handle camera positioning for external request (helper function)
        if "M362 OctoPNP_camera_external" in cmd:
            result = self._grabImages("HEAD")

            # the current printjob is resumed and octoPNP is set into default state
            # before returning the obtained image by callback to allow recursive executions
            # of the camera_helper by 3. party plugins (the camera helper is triggered from within the callback method).

            # resume paused printjob into normal operation
            if (self._printer.is_paused() or self._printer.is_pausing()) and not self._helper_was_paused:
                self._printer.resume_print()

            # leave external state
            self._state = self.STATE_NONE

            if result:
                if self._helper_callback:
                    self._helper_callback(self._settings.get(["camera", "head", "path"]))
            else:
                if self._helper_callback:
                    self._helper_callback(False)

            if not self._helper_callback:
                self._logger.info("Unable to return image to calling plugin, invalid callback")

            # suppress the magic command (M365)
            return (None,)


    def _moveCameraToPart(self, partnr):
        # switch to camera tool
        self._printer.commands("T" + str(self._settings.get(["camera", "head", "tool_nr"])))
        # move camera to part position
        tray_offset = self._getTrayPosFromPartNr(partnr) # get box position on tray
        camera_offset = [tray_offset[0]-float(self._settings.get(["camera", "head", "x"])), tray_offset[1]-float(self._settings.get(["camera", "head", "y"])), float(self._settings.get(["camera", "head", "z"])) + tray_offset[2]]
        cmd = "G1 X" + str(camera_offset[0]) + " Y" + str(camera_offset[1]) + " F" + str(self.FEEDRATE)
        self._logger.info("Move camera to: " + cmd)
        self._printer.commands("G91") # relative positioning
        self._printer.commands("G1 Z5 F" + str(self.FEEDRATE)) # lift printhead
        if(self._settings.get(["tray", "axis"]) != "Z"):
            self._printer.commands("G1 " + self._settings.get(["tray", "axis"]) + str(camera_offset[2]+5)) # lower tray
        self._printer.commands("G90") # absolute positioning
        self._printer.commands(cmd)
        self._printer.commands("G1 " + self._settings.get(["tray", "axis"]) + str(camera_offset[2]) + " F" + str(self.FEEDRATE)) # move tray to camera


    def _pickPart(self, partnr):
        part_offset = [0, 0]

        if(self._settings.get(["tray", "type"]) == "BOX"):
            self._logger.info("Taking head picture NOW") # Debug output

            # take picture
            if self._grabImages("HEAD"):
                headPath = self._settings.get(["camera", "head", "path"])

                #update UI
                self._updateUI("HEADIMAGE", headPath)

                #extract position information
                part_offset = self.imgproc.locatePartInBox(headPath, True)
                if not part_offset:
                    self._updateUI("ERROR", self.imgproc.getLastErrorMessage())
                    part_offset = [0, 0]
                else:
                    # update UI
                    self._updateUI("HEADIMAGE", self.imgproc.getLastSavedImagePath())

                    # Log image for debugging and documentation
                    if self._settings.get(["camera", "image_logging"]): self._saveDebugImage(headPath)
            else:
                cm_x=cm_y=0
                self._updateUI("ERROR", "Camera not ready")

            self._logger.info("PART OFFSET:" + str(part_offset))

            # disable head camera LEDs
            if(len(self._settings.get(["camera", "head", "disable_LED_gcode"])) > 0):
                self._printer.commands(self._settings.get(["camera", "head", "disable_LED_gcode"]))

        # and enable bed camera LEDs
        if(len(self._settings.get(["camera", "bed", "enable_LED_gcode"])) > 0):
            self._printer.commands(self._settings.get(["camera", "bed", "enable_LED_gcode"]))

        tray_offset = self._getTrayPosFromPartNr(partnr)
        vacuum_dest = [tray_offset[0]+part_offset[0],\
                         tray_offset[1]+part_offset[1],\
                         tray_offset[2]-float(self._settings.get(["vacnozzle", "z_pressure"]))]

        if(self._settings.get(["tray", "type"]) == "BOX"):
            vacuum_dest[2] += self.smdparts.getPartHeight(partnr)

        # only apply X/Y offsets if not handled by the firmware
        if(self._settings.get(["vacnozzle", "use_offsets"])):
            vacuum_dest[0] -= float(self._settings.get(["vacnozzle", "x"]))
            vacuum_dest[1] -= float(self._settings.get(["vacnozzle", "y"]))

        tray_axis = str(self._settings.get(["tray", "axis"]))

        # move vac nozzle to part and pick
        self._printer.commands("T" + str(self._settings.get(["vacnozzle", "tool_nr"])))
        self._printer.commands("M400")
        self._printer.commands("M400")
        if(tray_axis != "Z"):
            self._printer.commands("G1 " + tray_axis + str(vacuum_dest[2]+5))
            self._printer.commands("M400")
            self._printer.commands("M400")
        self._printer.commands("G1 X" + str(vacuum_dest[0]) + " Y" + str(vacuum_dest[1]) + " F" + str(self.FEEDRATE))
        self._printer.commands("M400")
        self._printer.commands("M400")
        if(tray_axis == "Z"):
            self._printer.commands("G1 Z" + str(vacuum_dest[2]+10))
            self._printer.commands("M400")
            self._printer.commands("M400")
        self._releaseVacuum()
        self._lowerVacuumNozzle()
        self._printer.commands("G1 " + tray_axis + str(vacuum_dest[2]) + " F1000")
        self._printer.commands("M400")
        self._printer.commands("M400")
        self._gripVacuum()
        self._printer.commands("G4 S1")
        self._printer.commands("G1 " + tray_axis + str(vacuum_dest[2]+5) + " F1000")
        self._printer.commands("M400")
        self._printer.commands("M400")

        # move to bed camera
        vacuum_dest = [float(self._settings.get(["camera", "bed", "x"])),\
                       float(self._settings.get(["camera", "bed", "y"])),\
                       float(self._settings.get(["camera", "bed", "z"]))+self.smdparts.getPartHeight(partnr)]

        # only apply X/Y offsets if not handled by the firmware
        if(self._settings.get(["vacnozzle", "use_offsets"])):
            vacuum_dest[0] -= float(self._settings.get(["vacnozzle", "x"]))
            vacuum_dest[1] -= float(self._settings.get(["vacnozzle", "y"]))

        tray_axis = str(self._settings.get(["tray", "axis"]))

        self._printer.commands("G1 X" + str(vacuum_dest[0]) + " Y" + str(vacuum_dest[1]) + " F"  + str(self.FEEDRATE))
        self._printer.commands("M400")

        # find destination at the object
        destination = self.smdparts.getPartDestination(partnr)
        #rotate object
        self._printer.commands("G92 E0")
        self._printer.commands("G1 E" + str(destination[3] + tray_offset[3]) + " F" + str(self.FEEDRATE))

        camera_axis = str(self._settings.get(["camera", "bed", "focus_axis"]))
        if(len(camera_axis) > 0):
            self._printer.commands("G1 " + camera_axis + str(vacuum_dest[2]) + " F"  + str(self.FEEDRATE))
        self._logger.info("Moving to bed camera")

    def _alignPart(self, partnr):
        orientation_offset = 0

        # take picture
        self._logger.info("Taking bed align picture NOW")
        bedPath = self._settings.get(["camera", "bed", "path"])
        if self._grabImages("BED"):
            #update UI
            self._updateUI("BEDIMAGE", bedPath)

            # get rotation offset
            orientation_offset = self.imgproc.getPartOrientation(bedPath, float(self._settings.get(["camera", "bed", "pxPerMM", "x"])), 0)
            if not orientation_offset:
                self._updateUI("ERROR", self.imgproc.getLastErrorMessage())
                orientation_offset = 0.0
            # update UI
            self._updateUI("BEDIMAGE", self.imgproc.getLastSavedImagePath())

            # Log image for debugging and documentation
            if self._settings.get(["camera", "image_logging"]): self._saveDebugImage(bedPath)
        else:
            self._updateUI("ERROR", "Camera not ready")

        #rotate object
        self._printer.commands("G92 E0")
        self._printer.commands("G1 E" + str(orientation_offset) + " F" + str(self.FEEDRATE))

    def _placePart(self, partnr):
        displacement = [0, 0]

        # find destination at the object
        destination = self.smdparts.getPartDestination(partnr)

        # take picture to find part offset
        self._logger.info("Taking bed offset picture NOW")
        bedPath = self._settings.get(["camera", "bed", "path"])
        orientation_offset = 0.0
        if self._grabImages("BED"):

            orientation_offset = self.imgproc.getPartOrientation(bedPath, float(self._settings.get(["camera", "bed", "pxPerMM", "x"])), destination[3])
            if not orientation_offset:
                self._updateUI("ERROR", self.imgproc.getLastErrorMessage())
                orientation_offset = 0.0

            displacement = self.imgproc.getPartPosition(bedPath, float(self._settings.get(["camera", "bed", "pxPerMM", "x"])))
            if not displacement:
                self._updateUI("ERROR", self.imgproc.getLastErrorMessage())
                displacement = [0, 0]

            #update UI
            self._updateUI("BEDIMAGE", self.imgproc.getLastSavedImagePath())

            # Log image for debugging and documentation
            if self._settings.get(["camera", "image_logging"]):
                self._saveDebugImage(bedPath)
            else:
                self._updateUI("ERROR", "Camera not ready")

        self._logger.info("displacement - x: " + str(displacement[0]) + " y: " + str(displacement[1]))

        # Double check whether orientation is now correct. Important on unreliable hardware...
        if(abs(orientation_offset) > 0.5):
            self._updateUI("INFO", "Incorrect alignment, correcting offset of " + str(-orientation_offset) + "°")
            self._logger.info("Incorrect alignment, correcting offset of " + str(-orientation_offset) + "°")
            self._printer.commands("G92 E0")
            self._printer.commands("G1 E" + str(orientation_offset) + " F" + str(self.FEEDRATE))
            # wait a second to execute the rotation
            time.sleep(2)
            # take another image for UI
            if self._grabImages("BED"):

                displacement = self.imgproc.getPartPosition(bedPath, float(self._settings.get(["camera", "bed", "pxPerMM", "x"])))
                #update UI
                self._updateUI("BEDIMAGE", self.imgproc.getLastSavedImagePath())

                # Log image for debugging and documentation
                if self._settings.get(["camera", "image_logging"]): self._saveDebugImage(bedPath)
            else:
                self._updateUI("ERROR", "Camera not ready")

        # disable bed camera LEDs
        if(len(self._settings.get(["camera", "bed", "disable_LED_gcode"])) > 0):
            self._printer.commands(self._settings.get(["camera", "bed", "disable_LED_gcode"]))

        # move to destination
        dest_z = destination[2]+self.smdparts.getPartHeight(partnr)-float(self._settings.get(["vacnozzle", "z_pressure"]))

       # only apply X/Y offsets if not handled by the firmware
        if(self._settings.get(["vacnozzle", "use_offsets"])):
            cmd = "G1 X" + str(destination[0]-float(self._settings.get(["vacnozzle", "x"]))+displacement[0]) \
                + " Y" + str(destination[1]-float(self._settings.get(["vacnozzle", "y"]))+displacement[1]) \
                + " F" + str(self.FEEDRATE)
        else:
            cmd = "G1 X" + str(destination[0]+displacement[0]) \
                + " Y" + str(destination[1]+displacement[1]) \
                + " F" + str(self.FEEDRATE)

        self._logger.info("object destination: " + cmd)
        self._printer.commands("G1 Z" + str(dest_z+10) + " F" + str(self.FEEDRATE)) # lift printhead
        self._printer.commands(cmd)
        self._printer.commands("G1 Z" + str(dest_z))

        #release part
        self._releaseVacuum()
        self._printer.commands("G4 S2") #some extra time to make sure the part has released and the remaining vacuum is gone
        self._printer.commands("G1 Z" + str(dest_z+10) + " F" + str(self.FEEDRATE)) # lift printhead again
        self._liftVacuumNozzle()

    # get the position of the box (center of the box) containing part x relative to the [0,0] corner of the tray
    def _getTrayPosFromPartNr(self, partnr):
        partPos = self.smdparts.getPartPosition(int(partnr))
        row = partPos["row"]
        col = partPos["col"]
        self._logger.info("Selected object: %d. Position: row %d, col %d", partnr, row, col)

        x = 0.0
        y = 0.0
        rotation = 0.0

        if(self._settings.get(["tray", "type"]) == "BOX"):
            boxsize = float(self._settings.get(["tray", "box", "boxsize"]))
            rimsize = float(self._settings.get(["tray", "box", "rimsize"]))
            x = (col-1)*boxsize + boxsize/2 + col*rimsize
            y = (row-1)*boxsize + boxsize/2 + row*rimsize

        if(self._settings.get(["tray", "type"]) == "FEEDER"):
            feederconfig = self._settings.get(["tray", "feeder", "feederconfiguration"])
            for i in range(1, row+1):
                y += float(feederconfig[i]["width"]) + float(self._settings.get(["tray", "feeder", "row_clearance"]))

            # y should now be the point marker in the correct row
            # 1.75mm for punch-hole line + measured offset
            y -= 0.5*(float(feederconfig[row]["width"])) - 0.45

            # x pos starts from point marker. Add number of components plus 1/2 component
            x += (col+0.5)  * float(feederconfig[row]["spacing"])
            if(float(feederconfig[row]["spacing"]) > 4):
                x -= 2.0


            # rotation of this row
            rotation = float(feederconfig[row]["rotation"])


        return [x + float(self._settings.get(["tray", "x"])), y + float(self._settings.get(["tray", "y"])), float(self._settings.get(["tray", "z"])), rotation]

    def _gripVacuum(self):
        self._printer.commands("M400")
        self._printer.commands("M400")
        self._printer.commands("G4 S1")
        for line in self._settings.get(["vacnozzle", "grip_vacuum_gcode"]).splitlines():
            self._printer.commands(line)
        self._printer.commands("G4 S1")

    def _releaseVacuum(self):
        self._printer.commands("M400")
        self._printer.commands("M400")
        self._printer.commands("G4 S1")
        for line in self._settings.get(["vacnozzle", "release_vacuum_gcode"]).splitlines():
            self._printer.commands(line)
        self._printer.commands("G4 S1")

    def _lowerVacuumNozzle(self):
        self._printer.commands("M400")
        self._printer.commands("M400")
        self._printer.commands("G4 S1")
        for line in self._settings.get(["vacnozzle", "lower_nozzle_gcode"]).splitlines():
            self._printer.commands(line)
        self._printer.commands("G4 S1")

    def _liftVacuumNozzle(self):
        self._printer.commands("M400")
        self._printer.commands("M400")
        self._printer.commands("G4 S1")
        for line in self._settings.get(["vacnozzle", "lift_nozzle_gcode"]).splitlines():
            self._printer.commands(line)
        self._printer.commands("G4 S1")

    def _grabImages(self, camera):
        result = True
        grabScript = ""
        if(camera == "HEAD"):
            grabScript = self._settings.get(["camera", "head", "grab_script_path"])
        if(camera == "BED"):
            grabScript = self._settings.get(["camera", "bed", "grab_script_path"])
        #os.path.dirname(os.path.realpath(__file__)) + "/cameras/grab.sh"
        try:
            if call([grabScript]) != 0:
                self._logger.info("ERROR: " + camera + " camera not ready!")
                result = False
        except:
            self._logger.info("ERROR: Unable to execute " + camera + " camera grab script!")
            self._logger.info("Script path: " + grabScript)
            result = False
        return result

    def _saveDebugImage(self, path):
        name, ext = os.path.splitext(os.path.basename(path))
        timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d-%H:%M:%S')
        filename = "/" + name + "_" + timestamp + ext
        dest_path = os.path.dirname(path) + filename
        shutil.copy(path, dest_path)
        self._logger.info("saved %s image to %s", name, dest_path)


    def _updateUI(self, event, parameter):
        data = dict(
            info="dummy"
        )
        if event == "FILE":
            if self.smdparts.isFileLoaded():

                # compile part information
                partIds = self.smdparts.getPartIds()
                partArray = []
                partPos = 1
                for partId in partIds:
                    # assign components to tray boxes.
                    if(self._settings.get(["tray", "type"]) == "BOX"):
                        row = int((partPos-1)/int(self._settings.get(["tray", "box", "columns"]))+1)
                        col = ((partPos-1)%int(self._settings.get(["tray", "box", "columns"])))+1
                        self.smdparts.setPartPosition(partId, row, col)
                        partPos += 1
                    partArray.append(
                        dict(
                            id = partId,
                            name = self.smdparts.getPartName(partId),
                            row = self.smdparts.getPartPosition(partId)["row"],
                            col = self.smdparts.getPartPosition(partId)["col"],
                            shape = self.smdparts.getPartShape(partId),
                            pads = self.smdparts.getPartPads(partId)
                        )
                    )

                data = dict(
                    partCount = self.smdparts.getPartCount(),
                    parts = partArray
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
        elif event == "INFO":
            data = dict(
                type = parameter,
            )
        elif event is "HEADIMAGE" or event is "BEDIMAGE":
            # open image and convert to base64
            f = open(parameter,"rb")
            data = dict(
                src = "data:image/" + os.path.splitext(parameter)[1] + ";base64,"+str(base64.b64encode(bytes(f.read())), "utf-8")
            )

        message = dict(
            event=event,
            data=data
        )
        self._pluginManager.send_plugin_message("OctoPNP", message)



    # Helper function to provide camera access to other plugins.
    # Returns resolution for 'camera' (HEAD or BED) as a dict with "x" and "y".
    def _helper_get_head_camera_pxPerMM(self, camera):
        if camera == "HEAD":
            return dict(
                x = float(self._settings.get(["camera", "head", "pxPerMM", "x"])),
                y = float(self._settings.get(["camera", "head", "pxPerMM", "y"]))
            )
        if camera == "BED":
            return dict(
                x = float(self._settings.get(["camera", "bed", "pxPerMM", "x"])),
                y = float(self._settings.get(["camera", "bed", "pxPerMM", "y"]))
            )
        return 0.0


    # Helper function to provide camera access to other plugins.
    # Moves printhead with camera to given x/y coordinates, takes
    # a picture and returns by invoking the callback function.
    # Can only be used for the head camera, since bed camera is fixed and can't be moved to a x/y coordinate.
    #
    # adjust_focus: add camera focus distance to current z position.
    # Can be disabled to take multiple shots without moving the z-axis
    def _helper_get_head_camera_image_xy(self, x, y, callback, adjust_focus=True):
        result = False

        self._logger.info("Trying to take image at pos [" + str(x) + ":" + str(y) + "] for external plugin")

        if self._state == self.STATE_NONE:
            self._state = self.STATE_EXTERNAL
            result = True
            self._helper_was_paused = False
            if self._printer.is_paused() or self._printer.is_pausing():
                self._helper_was_paused = True
            if self._printer.is_printing() or self._printer.is_resuming(): # interrupt running printjobs to prevent octoprint from sending further gcode lines from the file
                self._printer.pause_print()

            # store callback
            self._helper_callback = callback

            target_position = [x-float(self._settings.get(["camera", "head", "x"])), y-float(self._settings.get(["camera", "head", "y"])), float(self._settings.get(["camera", "head", "z"]))]
            cmd = "G1 X" + str(target_position[0]) + " Y" + str(target_position[1]) + " F" + str(self.FEEDRATE)

            # switch to primary extruder, since the head camera is relative to this extruder and the offset to PNP nozzle might not be known (firmware offset)
            self._printer.commands("T0")

            if adjust_focus:
                self._printer.commands("G91") # relative positioning
                self._printer.commands("G1 Z" + str(target_position[2]) + " F" + str(self.FEEDRATE)) # lift printhead
                self._printer.commands("G90") # absolute positioning
            self._printer.commands(cmd)

            self._printer.commands("M400")
            self._printer.commands("G4 P1")
            self._printer.commands("M400")
            for i in range(10):
                self._printer.commands("G4 P1")
            self._printer.commands("M362 OctoPNP_camera_external")

        else:
            self._logger.info("Abort, OctoPNP is busy (not in state NONE, current state: " + str(self._state) + ")")

        return result
