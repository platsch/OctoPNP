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


import json
import re
from subprocess import call
from collections import namedtuple
import os
import time
import datetime
import base64
import shutil
import flask
import octoprint.plugin

from .SmdParts import SmdParts
from .ImageProcessing import ImageProcessing


# pylint: disable=attribute-defined-outside-init
__plugin_name__ = "OctoPNP"
__plugin_pythoncompat__ = ">=2.7,<4"
__plugin_implementation__ = ""
__plugin_hooks__ = {}
__plugin_helpers__ = {}

# instantiate plugin object and register hook for gcode injection
def __plugin_load__():

    octopnp = OctoPNP()

    # pylint: disable=global-statement
    global __plugin_implementation__
    __plugin_implementation__ = octopnp

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.comm.protocol.gcode.sending": octopnp.hook_gcode_sending,
        "octoprint.comm.protocol.gcode.queuing": octopnp.hook_gcode_queuing,
    }

    global __plugin_helpers__
    __plugin_helpers__ = dict(
        get_head_camera_pxPerMM = octopnp.helper_get_head_camera_pxPerMM,
        get_head_camera_image = octopnp.helper_get_head_camera_image_xy
        # parameter: [x, y, callback, adjust_focus=True]
    )


class OctoPNP(
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.BlueprintPlugin,
):

    STATE_NONE = 0
    STATE_PICK = 1
    STATE_ALIGN = 2
    STATE_PLACE = 3
    STATE_EXTERNAL = 9  # used if helper functions are called by external plugins

    FEEDRATE = 4000.000

    smdparts = SmdParts()
    partPositions = {}

    def __init__(self):
        # pylint: disable=super-init-not-called
        self._state = self.STATE_NONE
        self._currentPart = 0
        self._helper_was_paused = False

        # store callback to send result of an image capture request back to caller
        self._helper_callback = None

    def on_after_startup(self):
        self.imgproc = ImageProcessing(
            float(self._settings.get(["tray", "box", "boxsize"])),
            int(self._settings.get(["camera", "bed", "binary_thresh"])),
            int(self._settings.get(["camera", "head", "binary_thresh"])),
        )
        # used for communication to UI
        self._pluginManager = octoprint.plugin.plugin_manager()

    def get_settings_defaults(self):
        return {
            "tray": {
                # general settings applying to all tray types
                "x": 0,
                "y": 0,
                "z": 0,
                "axis": "Z",
                "type": "BOX",  # possible alternatives: FEEDER
                # type specific settings
                "box": {
                    "rows": 5,
                    "columns": 5,
                    "boxsize": 10,
                    "rimsize": 1.0,
                },
                "feeder": {
                    "row_clearance": 3.0,
                    "feederconfiguration": [
                        {"width": 8.0, "spacing": 5.0, "rotation": 0},
                        {"width": 12.0, "spacing": 8.0, "rotation": 90},
                    ],
                },
                "nut": {
                    "rows": 5,
                    "columns": 5,
                    "boxsize": 10,
                    "centerToCenter": 0,
                    "partRotationFlat": 0,
                    "partRotationUpright": 0,
                    "boxconfiguration": "[ {\"thread_size\": \"2\", \"nut\": \"hexnut\", \"slot_orientation\": \"upright\"},   {\"thread_size\": \"2.5\", \"nut\": \"hexnut\", \"slot_orientation\": \"upright\"},   {\"thread_size\": \"3\", \"nut\": \"hexnut\", \"slot_orientation\": \"flat\"},   {\"thread_size\": \"8\", \"nut\": \"hexnut\", \"slot_orientation\": \"upright\"},   {\"thread_size\": \"8\", \"nut\": \"hexnut\", \"slot_orientation\": \"flat\"},   {\"thread_size\": \"3\", \"nut\": \"squarenut\", \"slot_orientation\": \"upright\"},   {\"thread_size\": \"10\", \"nut\": \"squarenut\", \"slot_orientation\": \"flat\"},   {\"thread_size\": \"8\", \"nut\": \"squarenut\", \"slot_orientation\": \"upright\"},   {\"thread_size\": \"6\", \"nut\": \"squarenut\", \"slot_orientation\": \"flat\"},   {\"thread_size\": \"4\", \"nut\": \"squarenut\", \"slot_orientation\": \"upright\"} ]"
                }
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
                "lift_nozzle_gcode": "",
            },
            "magnetnozzle": {
                "use_offsets": False,
                "x": 0,
                "y": 0,
                "tool_nr": 2,
                "grip_magnet_gcode": "M42 P48 S255",
                "release_magnet_gcode": "M42 P48 S0",
                "lower_nozzle_gcode": "",
                "lift_nozzle_gcode": ""
            },
            "camera": {
                "head": {
                    "x": 0,
                    "y": 0,
                    "z": 0,
                    "tool_nr": 0,
                    "pxPerMM": {"x": 50.0, "y": 50.0},
                    "enable_LED_gcode": "",
                    "disable_LED_gcode": "",
                    "path": "",
                    "binary_thresh": 150,
                    "grab_script_path": "",
                    "http_path": "",
                },
                "bed": {
                    "x": 0,
                    "y": 0,
                    "z": 0,
                    "focus_axis": "Z",
                    "pxPerMM": {"x": 50.0, "y": 50.0},
                    "enable_LED_gcode": "",
                    "disable_LED_gcode": "",
                    "path": "",
                    "binary_thresh": 150,
                    "grab_script_path": "",
                    "http_path": "",
                },
                "image_logging": False,
            },
            "calibration": {"toolchange_gcode": "G1 X100 Y150 F3000"},
        }

    def get_template_configs(self):
        return [
            dict(type="tab", template="OctoPNP_tab.jinja2", custom_bindings=True),
            dict(
                type="settings",
                template="OctoPNP_settings.jinja2",
                custom_bindings=True,
            )
            # dict(type="settings", custom_bindings=True)
        ]

    def get_assets(self):
        return dict(
            js=[
                "js/OctoPNP.js",
                "js/settings.js",
                "js/boxTray.js",
                "js/feederTray.js",
                "js/nutTray.js",
                "js/trayUtil.js",
            ]
        )

    # Flask endpoint for the GUI to request camera images.
    # Possible request parameters are "BED" and "HEAD".
    @octoprint.plugin.BlueprintPlugin.route("/camera_image", methods=["GET"])
    def getCameraImage(self):
        result = ""
        if "imagetype" in flask.request.values:
            camera = flask.request.values["imagetype"]
            if camera in ("HEAD", "BED"):
                if self._grabImages(camera):
                    imagePath = self._settings.get(["camera", camera.lower(), "path"])
                    try:
                        with open(imagePath, "rb") as f:
                            result = flask.jsonify(
                                src="data:image/{0};base64,{1}".format(
                                    os.path.splitext(imagePath)[1],
                                    str(base64.b64encode(bytes(f.read())), "utf-8"))
                            )
                    except IOError:
                        result = flask.jsonify(
                            error="Unable to open Image after fetching. Image path: "
                            + imagePath
                        )
                else:
                    result = flask.jsonify(
                        error="Unable to fetch image. Check octoprint log for details."
                    )
        return flask.make_response(result, 200)

    # Flask endpoint for the GUI to update component tray assignments
    @octoprint.plugin.BlueprintPlugin.route("/tray_assignments", methods=["GET"])
    def updateTrayAssignments(self):
        if "mapping" in flask.request.values:
            mapping = flask.request.values["mapping"]
            mapping = json.loads(mapping)
            for part in mapping:
                self.smdparts.setPartPosition(
                    int(part), int(mapping[part]["row"]), int(mapping[part]["col"])
                )
        return flask.make_response("", 200)

    # Use the on_event hook to extract XML data every time a new file has been loaded by the user
    def on_event(self, event, payload):
        # extraxt part informations from inline xmly
        if event == "FileSelected":
            self._currentPart = None
            xml = ""
            gcode_path = self._file_manager.path_on_disk(
                payload.get("origin"), payload.get("path")
            )
            with open(gcode_path, "r", encoding='utf-8') as f:
                for line in f:
                    expression = re.search("<.*>", line)
                    if expression:
                        xml += expression.group() + "\n"
            if xml:
                # check for root node existence
                if not re.search("<object.*>", xml.splitlines()[0]):
                    xml = '<object name="defaultpart">\n' + xml + "\n</object>"

                # parse xml data
                msg = self.smdparts.load(xml)
                if msg == "":
                    # TODO: validate part informations against tray
                    self._logger.info(
                        "Extracted information on %d parts from gcode file %s",
                        self.smdparts.getPartCount(),
                        payload.get("name")
                    )
                    self._updateUI("FILE", "")
                else:
                    self._logger.error("XML parsing error: " + msg)
                    self._updateUI("ERROR", "XML parsing error: " + msg)
            else:
                # gcode file contains no part information -> clear smdpart object
                self.smdparts.unload()
                self._updateUI("FILE", "")

    def __set_cam_LED(self, cam, act):
        if len(self._settings.get(["camera", cam, act])) > 0:
            self._printer.commands(self._settings.get(["camera", cam, act]))

#   """
#   Use the gcode hook to interrupt the printing job on custom M361 commands.
#   """

    def hook_gcode_queuing(
        self, _comm_instance, _phase, cmd, _cmd_type, _gcode, *_args, **_kwargs
    ):
        if "M361" in cmd:
            if self._state == self.STATE_NONE:
                self._state = self.STATE_PICK
                command = re.search(r"P\d*", cmd).group()  # strip the M361
                self._currentPart = int(command[1:])

                self._logger.info(
                    "Received M361 command to place part: " + str(self._currentPart)
                )

                # pause running printjob to prevent octoprint from sending new commands
                # from the gcode file during the interactive PnP process
                if self._printer.is_printing() or self._printer.is_resuming():
                    self._printer.pause_print()

                self._updateUI("OPERATION", "pick")

                if self._settings.get(["tray", "type"]) == "BOX":
                    # enable head camera LEDs
                    self.__set_cam_LED("head", "enable_LED_gcode")
                    self._logger.info("Move camera to part: " + str(self._currentPart))
                    self._moveCameraToPart(self._currentPart)

                self._printer.commands("M400")
                self._printer.commands("G4 P1")
                self._printer.commands("M400")
                for _ in range(10):
                    self._printer.commands("G4 P1")

                self._printer.commands("M362 OctoPNP")
            else:
                self._logger.error(
                    "Received M361 command while placing part: " + str(self._currentPart)
                )

    def __helper_gcode_sending(self):
        self._printer.commands("M400")
        self._printer.commands("G4 P1")
        self._printer.commands("M400")

    # The current printjob is resumed and octoPNP is set into default state before
    # returning the obtained image by callback to allow recursive executions of the
    # camera_helper by 3. party plugins (the camera helper is triggered from within
    # the callback method).
    def __M362_OctoPNP_camera_external(self):
        result = self._grabImages("HEAD")
        # resume paused printjob into normal operation
        if (self._printer.is_paused() or self._printer.is_pausing()
            ) and not self._helper_was_paused:
            self._printer.resume_print()
        # leave external state
        self._state = self.STATE_NONE
        if self._helper_callback:
            if result:
                self._helper_callback(self._settings.get(["camera", "head", "path"]))
            else:
                self._helper_callback(False)
        else:
            self._logger.info("Unable to return image to calling plugin, invalid callback")

#   """
#   This hook is designed as some kind of a "state machine". The reason is, that we have to
#   circumvent the buffered gcode execution in the printer. To take a picture, the buffer must be
#   emptied to ensure that the printer has executed all previous moves and is now at the desired
#   position. To achieve this, a M400 command is injected after the camera positioning command,
#   followed by a M362. This causes the printer to send the next acknowledging ok not until the
#   positioning is finished. Since the next command is a M362, octoprint will call the gcode hook
#   again and we are back in the game, iterating to the next state. Since both, Octoprint and the
#   printer firmware are using a queue, we inject some "G4 P1" commands as a "clearance buffer".
#   Those commands simply cause the printer to wait for a millisecond.
#   """

    # pylint: disable=inconsistent-return-statements
    def hook_gcode_sending(
        self, _comm_instance, _phase, cmd, _cmd_type, _gcode, *_args, **_kwargs
    ):
        if "M362 OctoPNP" in cmd:
            if self._state == self.STATE_PICK:
                self._state = self.STATE_ALIGN
                self._logger.info("Pick part " + str(self._currentPart))

                # generate new imageProcessing object with updated settings
                self.imgproc = ImageProcessing(
                    float(self._settings.get(["tray", "box", "boxsize"])),
                    int(self._settings.get(["camera", "bed", "binary_thresh"])),
                    int(self._settings.get(["camera", "head", "binary_thresh"])),
                )

                self._pickPart(self._currentPart)
                self.__helper_gcode_sending()

                for _ in range(10):
                    self._printer.commands("G4 P1")

                self._printer.commands("M362 OctoPNP")

                return (None,)  # suppress command

            if self._state == self.STATE_ALIGN:
                self._state = self.STATE_PLACE
                self._logger.info("Align part " + str(self._currentPart))

                self._alignPart()
                self.__helper_gcode_sending()

                # still having trouble with images taken before alignment was fully executed...
                self._printer.commands("G4 S2")

                for _ in range(10):
                    self._printer.commands("G4 P1")

                self._printer.commands("M362 OctoPNP")

                return (None,)  # suppress command

            if self._state == self.STATE_PLACE:
                self._logger.info("Place part " + str(self._currentPart))

                self._placePart(self._currentPart)
                self.__helper_gcode_sending()

                for _ in range(10):
                    self._printer.commands("G4 P1")

                self._logger.info("Finished placing part " + str(self._currentPart))
                self._state = self.STATE_NONE

                # resume paused printjob into normal operation
                if self._printer.is_paused() or self._printer.is_pausing():
                    self._printer.resume_print()

                return (None,)  # suppress command

        # handle camera positioning for external request (helper function)
        if "M362 OctoPNP_camera_external" in cmd:
            self.__M362_OctoPNP_camera_external()
            # suppress the magic command (M365)
            return (None,)

    def _moveCameraToPart(self, partnr):
        # switch to camera tool
        self._printer.commands("T" + str(self._settings.get(["camera", "head", "tool_nr"])))
        # move camera to part position
        tray_offset = self._getTrayPosFromPartNr(partnr)  # get box position on tray
        camera_offset = namedtuple('cam', 'x y z')(
            tray_offset["x"] - float(self._settings.get(["camera", "head", "x"])),
            tray_offset["y"] - float(self._settings.get(["camera", "head", "y"])),
            tray_offset["z"] + float(self._settings.get(["camera", "head", "z"])))

        cmd = "G1 X{0} Y{1} F{2}".format(camera_offset.x, camera_offset.y, self.FEEDRATE)

        self._logger.info("Move camera to: " + cmd)
        self._printer.commands("G91")  # relative positioning
        self._printer.commands("G1 Z5 F" + str(self.FEEDRATE))  # lift printhead
        if self._settings.get(["tray", "axis"]) != "Z":
            self._printer.commands("G1 {0}{1}".format(
                self._settings.get(["tray", "axis"]), camera_offset.z + 5))  # lower tray
        self._printer.commands("G90")  # absolute positioning
        self._printer.commands(cmd)
        self._printer.commands("G1 {0}{1} F{2}".format(
            self._settings.get(["tray", "axis"]), camera_offset.z, self.FEEDRATE)
        )  # move tray to camera

    def __get_part_offset(self):
        part_offset = namedtuple('displacement', 'x y')(0, 0)
        if self._settings.get(["tray", "type"]) == "BOX":
            self._logger.info("Taking head picture NOW")  # Debug output

            # take picture
            if self._grabImages("HEAD"):
                headPath = self._settings.get(["camera", "head", "path"])

                # update UI
                self._updateUI("HEADIMAGE", headPath)

                # extract position information
                part_offset = self.imgproc.locatePartInBox(headPath, True)
                if part_offset.x == 0 and part_offset.y == 0:
                    self._updateUI("ERROR", self.imgproc.getLastErrorMessage())
                else:
                    # update UI
                    self._updateUI("HEADIMAGE", self.imgproc.getLastSavedImagePath())

                    # Log image for debugging and documentation
                    if self._settings.get(["camera", "image_logging"]):
                        self._saveDebugImage(headPath)
            else:
                self._updateUI("ERROR", "Camera not ready")

            self._logger.info("PART OFFSET:" + str(part_offset))

            # disable head camera LEDs
            self.__set_cam_LED("head", "disable_LED_gcode")

        # and enable bed camera LEDs
        self.__set_cam_LED("bed", "enable_LED_gcode")
        return part_offset

    def __double_M400(self):
        self._printer.commands("M400")
        self._printer.commands("M400")

    def __rotate_obj(self, rot):
        self._printer.commands("G92 E0")
        self._printer.commands("G1 E{0} F{1}".format(rot, self.FEEDRATE))
        self._logger.info("object rotation: " + str(rot))

    def __move_magnet_to_part_and_pick(self, tool_dest):
        self._printer.commands("T" + str(self._settings.get(["magnet", "tool_nr"])))
        self._printer.commands("G1 X{0} Y{1} F{2}".format(
            tool_dest["x"], tool_dest["y"], self.FEEDRATE))
        self._printer.commands("G1 Z{0}".format(tool_dest["z"]+10))
        self._releaseMagnet()
        self._printer.commands("G1 Z{0} F1000".format(tool_dest["z"]))
        self._gripMagnet()
        self._printer.commands("G4 P500")
        self._printer.commands("G1 Z{0} F1000".format(tool_dest["z"]+5))

    def __move_vac_to_part_and_pick(self, tray_axis, tool_dest):
        self._printer.commands("T" + str(self._settings.get(["vacnozzle", "tool_nr"])))
        self.__double_M400()
        if tray_axis != "Z":
            self._printer.commands("G1 {0}{1}".format(tray_axis, tool_dest["z"] + 5))
            self.__double_M400()
        self._printer.commands("G1 X{0} Y{1} F{2}".format(
            tool_dest["x"], tool_dest["y"], self.FEEDRATE))
        self.__double_M400()
        if tray_axis == "Z":
            self._printer.commands("G1 Z{0}".format(tool_dest["z"] + 10))
            self.__double_M400()
        self._releaseVacuum()
        self._lowerVacuumNozzle()
        self._printer.commands("G1 {0}{1} F1000".format(tray_axis, tool_dest["z"]))
        self.__double_M400()
        self._gripVacuum()
        self._printer.commands("G4 S1")
        self._printer.commands("G1 {0}{1} F1000".format(tray_axis, tool_dest["z"] + 5))
        self.__double_M400()

    def _pickPart(self, partnr):
        part_offset = self.__get_part_offset()
        tray_offset = self._getTrayPosFromPartNr(partnr)
        tool = {"x": 0.0,"y": 0.0,"z": 0.0}

        if self._settings.get(["tray", "type"]) == "NUT":
            tool["x"] = float(self._settings.get(["magnetnozzle", "x"]))
            tool["y"] = float(self._settings.get(["magnetnozzle", "y"]))
        else:
            tool["z"] = float(self._settings.get(["vacnozzle", "z_pressure"]))

        tool_dest = {
            "x": tray_offset["x"] + part_offset.x - tool["x"],
            "y": tray_offset["y"] + part_offset.y - tool["y"],
            "z": tray_offset["z"] - tool["z"]}

        if tray_offset["type"] == "BOX":
            tool_dest["z"] += self.smdparts.getPartHeight(partnr)
        nozzleType = "vacnozzle"
        if self._settings.get(["tray", "type"]) == "NUT":
            nozzleType = "magnetnozzle"

        # only apply X/Y offsets if not handled by the firmware
        if self._settings.get([nozzleType, "use_offsets"]):
            tool_dest["x"] -= float(self._settings.get([nozzleType, "x"]))
            tool_dest["y"] -= float(self._settings.get([nozzleType, "y"]))

        tray_axis = str(self._settings.get(["tray", "axis"]))

        if self._settings.get(["tray", "type"]) == "NUT":
            self.__move_magnet_to_part_and_pick(tool_dest)
        else:
            self.__move_vac_to_part_and_pick(tray_axis, tool_dest)

            # move to bed camera
            tool_dest["x"] = float(self._settings.get(["camera", "bed", "x"]))
            tool_dest["y"] = float(self._settings.get(["camera", "bed", "y"]))
            tool_dest["z"] = float(self._settings.get(["camera", "bed", "z"])
                ) + self.smdparts.getPartHeight(partnr)

            # only apply X/Y offsets if not handled by the firmware
            if self._settings.get(["vacnozzle", "use_offsets"]):
                tool_dest["x"] -= float(self._settings.get(["vacnozzle", "x"]))
                tool_dest["y"] -= float(self._settings.get(["vacnozzle", "y"]))

            self._printer.commands(
                "G1 X{0} Y{1} F{2}".format(tool_dest["x"], tool_dest["y"], self.FEEDRATE)
            )
            self._printer.commands("M400")

            self.__rotate_obj(self.smdparts.getPartDestination(partnr)[3] + tray_offset["z"])

            camera_axis = str(self._settings.get(["camera", "bed", "focus_axis"]))
            if len(camera_axis) > 0:
                self._printer.commands(
                    "G1 {0}{1} F{2}".format(camera_axis, tool_dest["z"], self.FEEDRATE)
                )
            self._logger.info("Moving to bed camera")

    def __get_orientation_offset(self, bedPath):
        orientation_offset = self.imgproc.getPartOrientation(
            bedPath, float(self._settings.get(["camera", "bed", "pxPerMM", "x"])))
        if not orientation_offset:
            self._updateUI("ERROR", self.imgproc.getLastErrorMessage())
            orientation_offset = 0.0
        return orientation_offset

    def _alignPart(self):
        orientation_offset = 0.0

        # take picture
        self._logger.info("Taking bed align picture NOW")
        bedPath = self._settings.get(["camera", "bed", "path"])
        if self._grabImages("BED"):
            # update UI
            self._updateUI("BEDIMAGE", bedPath)

            # get rotation offset
            orientation_offset = self.__get_orientation_offset(bedPath)

            # update UI
            self._updateUI("BEDIMAGE", self.imgproc.getLastSavedImagePath())

            # Log image for debugging and documentation
            if self._settings.get(["camera", "image_logging"]):
                self._saveDebugImage(bedPath)
        else:
            self._updateUI("ERROR", "Camera not ready")

        self.__rotate_obj(orientation_offset)

    def _placePart(self, partnr):
        displacement = [0, 0]

        # find destination at the object
        destination = self.smdparts.getPartDestination(partnr)

        # take picture to find part offset
        self._logger.info("Taking bed offset picture NOW")
        bedPath = self._settings.get(["camera", "bed", "path"])
        orientation_offset = 0.0
        if self._grabImages("BED"):

            orientation_offset = self.__get_orientation_offset(bedPath)

            displacement = self.imgproc.getPartPosition(
                bedPath, float(self._settings.get(["camera", "bed", "pxPerMM", "x"]))
            )
            if not displacement:
                self._updateUI("ERROR", self.imgproc.getLastErrorMessage())
                displacement = [0, 0]

            # update UI
            self._updateUI("BEDIMAGE", self.imgproc.getLastSavedImagePath())

            # Log image for debugging and documentation
            if self._settings.get(["camera", "image_logging"]):
                self._saveDebugImage(bedPath)
            else:
                self._updateUI("ERROR", "Camera not ready")

        self._logger.info("displacement - x: {0} y: {1}".format(displacement[0], displacement[1]))

        # Double check whether orientation is now correct. Important on unreliable hardware...
        if abs(orientation_offset) > 0.5:
            msg = "Incorrect alignment, correcting offset of {0}°".format(-orientation_offset)
            self._updateUI("INFO", msg)
            self._logger.info(msg)
            self.__rotate_obj(orientation_offset)
            # wait a second to execute the rotation
            time.sleep(2)
            # take another image for UI
            if self._grabImages("BED"):

                displacement = self.imgproc.getPartPosition(
                    bedPath,
                    float(self._settings.get(["camera", "bed", "pxPerMM", "x"]))
                )
                # update UI
                self._updateUI("BEDIMAGE", self.imgproc.getLastSavedImagePath())

                # Log image for debugging and documentation
                if self._settings.get(["camera", "image_logging"]):
                    self._saveDebugImage(bedPath)
            else:
                self._updateUI("ERROR", "Camera not ready")

        # disable bed camera LEDs
        self.__set_cam_LED("bed", "disable_LED_gcode")

        # move to destination
        dest_z = (
            destination[2] + self.smdparts.getPartHeight(partnr)
            - float(self._settings.get(["vacnozzle", "z_pressure"]))
        )

        # only apply X/Y offsets if not handled by the firmware
        if self._settings.get(["vacnozzle", "use_offsets"]):
            destination[0] -= float(self._settings.get(["vacnozzle", "x"]))
            destination[1] -= float(self._settings.get(["vacnozzle", "y"]))
        cmd = "G1 X{0} Y{1} F{2}".format(
                destination[0] + displacement[0],
                destination[1] + displacement[1],
                self.FEEDRATE)

        self._logger.info("object destination: " + cmd)
        # lift printhead
        self._printer.commands("G1 Z{0} F{1}".format(dest_z + 10, self.FEEDRATE))
        self._printer.commands(cmd)
        self._printer.commands("G1 Z" + str(dest_z))

        # release part
        self._releaseVacuum()
        # some extra time to make sure the part has released and the remaining vacuum is gone
        self._printer.commands("G4 S2")
        # lift printhead again
        self._printer.commands("G1 Z{0} F{1}".format(dest_z + 10, self.FEEDRATE))
        self._liftVacuumNozzle()

    # Get the position of the box (center of the box) containing
    # part x relative to the [0,0] corner of the tray
    def _getTrayPosFromPartNr(self, partnr):
        partPos = self.smdparts.getPartPosition(int(partnr))
        row = partPos["row"]
        col = partPos["col"]
        self._logger.info(
            "Selected object: %d. Position: row %d, col %d", partnr, row, col
        )

        tray = {"x": 0.0,
                "y": 0.0,
                "z": float(self._settings.get(["tray", "z"])),
                "rotation": 0.0,
                "type": self._settings.get(["tray", "type"])}

        if tray["type"] == "BOX":
            boxsize = float(self._settings.get(["tray", "box", "boxsize"]))
            rimsize = float(self._settings.get(["tray", "box", "rimsize"]))
            tray["x"] = (col - 1) * boxsize + boxsize / 2 + col * rimsize
            tray["y"] = (row - 1) * boxsize + boxsize / 2 + row * rimsize

        if self._settings.get(["tray", "type"]) == "NUT":
            boxsize = float(self._settings.get(["tray", "nut", "boxsize"]))
            tray["x"] = col * boxsize + float(self._settings.get(["tray", "x"]))
            tray["y"] = row * boxsize + float(self._settings.get(["tray", "y"]))

        if tray["type"] == "FEEDER":
            feederconfig = self._settings.get(["tray", "feeder", "feederconfiguration"])
            for i in range(1, row + 1):
                tray["y"] += float(feederconfig[i]["width"]) + float(
                    self._settings.get(["tray", "feeder", "row_clearance"])
                )

            # y should now be the point marker in the correct row
            # 1.75mm for punch-hole line + measured offset
            tray["y"] -= 0.5 * (float(feederconfig[row]["width"])) - 0.45

            # x pos starts from point marker. Add number of components plus 1/2 component
            tray["x"] += (col + 0.5) * float(feederconfig[row]["spacing"])
            if float(feederconfig[row]["spacing"]) > 4:
                tray["x"] -= 2.0

            # rotation of this row
            tray["rotation"] = float(feederconfig[row]["rotation"])

            tray["x"] += float(self._settings.get(["tray", "x"]))
            tray["y"] += float(self._settings.get(["tray", "y"]))
        return tray

    def _gripMagnet(self):
        self._printer.commands("M400")
        self._printer.commands("M400")
        self._printer.commands("G4 P500")
        for line in self._settings.get(["magnetnozzle", "grip_magnet_gcode"]).splitlines():
            self._printer.commands(line)
        self._printer.commands("G4 P500")

    def _releaseMagnet(self):
        self._printer.commands("M400")
        self._printer.commands("M400")
        self._printer.commands("G4 P500")
        for line in self._settings.get(["magnetnozzle", "release_magnet_gcode"]).splitlines():
            self._printer.commands(line)
        self._printer.commands("G4 P500")

    def __vacuumNozzle(self, act):
        self.__double_M400()
        self._printer.commands("G4 S1")
        for line in self._settings.get(["vacnozzle", act]).splitlines():
            self._printer.commands(line)
        self._printer.commands("G4 S1")

    def _gripVacuum(self):
        self.__vacuumNozzle("grip_vacuum_gcode")

    def _releaseVacuum(self):
        self.__vacuumNozzle("release_vacuum_gcode")

    def _lowerVacuumNozzle(self):
        self.__vacuumNozzle("lower_nozzle_gcode")

    def _liftVacuumNozzle(self):
        self.__vacuumNozzle("lift_nozzle_gcode")

    def _grabImages(self, camera):
        result = True
        grabScript = ""
        if camera in ( "HEAD", "BED"):
            grabScript = self._settings.get(["camera", camera.lower(), "grab_script_path"])
        # os.path.dirname(os.path.realpath(__file__)) + "/cameras/grab.sh"
        try:
            if call([grabScript]) != 0:
                self._logger.error(camera + " camera not ready!")
                result = False
        except IOError:
            self._logger.error(
                "Unable to execute " + camera + " camera grab script!"
            )
            self._logger.info("Script path: " + grabScript)
            result = False
        return result

    def _saveDebugImage(self, path):
        name, ext = os.path.splitext(os.path.basename(path))
        timestamp = datetime.datetime.fromtimestamp(time.time()).strftime("%Y-%m-%d-%H:%M:%S")
        filename = "/" + name + "_" + timestamp + ext
        dest_path = os.path.dirname(path) + filename
        shutil.copy(path, dest_path)
        self._logger.info("saved %s image to %s", name, dest_path)

    def __event_file(self):
        if self.smdparts.isFileLoaded():
            # compile part information
            partIds = self.smdparts.getPartIds()
            self.partPositions = {}
            partArray = []
            partPos = 1
            usedTrayPositions = []
            config = json.loads(self._settings.get(["tray", "nut", "boxconfiguration"]))
            for partId in partIds:
                # assign components to tray boxes.
                if self._settings.get(["tray", "type"]) == "BOX":
                    row = int((partPos - 1)
                            / int(self._settings.get(["tray", "box", "columns"])) + 1)
                    col = ((partPos - 1)
                            % int(self._settings.get(["tray", "box", "columns"]))) + 1
                    self.smdparts.setPartPosition(partId, row, col)
                    partPos += 1

                    if self._settings.get(["tray", "type"]) == "NUT":
                        threadSize = self.smdparts.getPartThreadSize(partId)
                        partType = self.smdparts.getPartType(partId)
                        partOrientation = self.smdparts.getPartOrientation(partId).lower()
                        trayPosition = None
                        # find empty tray position, where the part fits
                        for i, traybox in enumerate(config):
                            if(float(traybox.get("thread_size")) == float(threadSize) and
                                traybox.get("nut") == partType and
                                traybox.get("slot_orientation") == partOrientation and
                                i not in usedTrayPositions):
                                usedTrayPositions.append(i)
                                trayPosition = i
                                self.partPositions[partId] = i
                                break
                        if trayPosition is None:
                            output_str = "Error, no tray box for part no " + \
                                str(partId) + \
                                " (" + \
                                partType + \
                                " M" + \
                                str(threadSize) + \
                                ", part orientation: " + \
                                partOrientation + \
                                ") left"
                            print(output_str)
                            self._updateUI(output_str)
                            return
                        partArray.append(
                            dict(
                                id = partId,
                                name = self.smdparts.getPartName(partId),
                                partPosition = trayPosition,
                                shape = self.smdparts.getPartShape(partId),
                                type=partType,
                                threadSize = threadSize,
                                partOrientation = partOrientation
                            )
                        )
                        continue # jumpover to next for loop iteration.

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
            return dict(partCount = self.smdparts.getPartCount(), parts = partArray)
        return dict(info="dummy")

    def _updateUI(self, event, parameter):
        data = dict(info="dummy")
        if event == "FILE":
            data = self.__event_file()
        elif event == "OPERATION":
            data = dict(type = parameter, part = self._currentPart)
        elif event == "ERROR":
            data = dict(type = parameter)
            if self._currentPart:
                data["part"] = self._currentPart
        elif event == "INFO":
            data = dict(type = parameter)
        elif event in ( "HEADIMAGE", "BEDIMAGE"):
            # open image and convert to base64
            with open(parameter, "rb") as f:
                data = dict(
                    src="data:image/{0};base64,{1}".format(
                        os.path.splitext(parameter)[1],
                        str(base64.b64encode(bytes(f.read())), "utf-8"))
                )

        message = dict(event=event, data=data)
        self._pluginManager.send_plugin_message("OctoPNP", message)

    # Helper function to provide camera access to other plugins.
    # Returns resolution for 'camera' (HEAD or BED) as a dict with "x" and "y".
    def helper_get_head_camera_pxPerMM(self, camera):
        if camera in ("HEAD", "BED"):
            return dict(
                x = float(self._settings.get(["camera", camera.lower(), "pxPerMM", "x"])),
                y = float(self._settings.get(["camera", camera.lower(), "pxPerMM", "y"]))
            )
        return 0.0

    # Helper function to provide camera access to other plugins. Moves printhead with camera to
    # given x/y coordinates, takes a picture and returns by invoking the callback function.
    # Can only be used for the head camera, since bed camera is fixed and can't be
    # moved to a x/y coordinate.
    #
    # adjust_focus: add camera focus distance to current z position.
    # Can be disabled to take multiple shots without moving the z-axis
    def helper_get_head_camera_image_xy(self, x, y, callback, adjust_focus=True):
        self._logger.info("Trying to take image at pos [{0}:{1}] for external plugin".format(x, y))

        if self._state == self.STATE_NONE:
            self._state = self.STATE_EXTERNAL
            self._helper_was_paused = False
            if self._printer.is_paused() or self._printer.is_pausing():
                self._helper_was_paused = True
            # interrupt running printjobs to prevent octoprint
            # from sending further gcode lines from the file
            if self._printer.is_printing() or self._printer.is_resuming():
                self._printer.pause_print()

            # store callback
            self._helper_callback = callback

            target_position = namedtuple('pos', 'x y z')(
                x - float(self._settings.get(["camera", "head", "x"])),
                y - float(self._settings.get(["camera", "head", "y"])),
                float(self._settings.get(["camera", "head", "z"])))
            cmd = "G1 X{0} Y{1} F{2}".format(target_position.x, target_position.y, self.FEEDRATE)

            # switch to primary extruder, since the head camera is relative to this extruder and
            # the offset to PNP nozzle might not be known (firmware offset)
            self._printer.commands("T0")

            if adjust_focus:
                self._printer.commands("G91")  # relative positioning
                # lift printhead
                self._printer.commands("G1 Z{0} F{1}".format(target_position.z, self.FEEDRATE))
                self._printer.commands("G90")  # absolute positioning
            self._printer.commands(cmd)

            self.__helper_gcode_sending()
            for _ in range(10):
                self._printer.commands("G4 P1")
            self._printer.commands("M362 OctoPNP_camera_external")
            return True

        self._logger.info(
            "Abort, OctoPNP is busy (not in state NONE, current state: {0})".format(self._state)
        )
        return False
