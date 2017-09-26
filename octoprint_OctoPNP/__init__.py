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

from __future__ import absolute_import


import octoprint.plugin
import flask
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

        # store callback to send result of an image capture request back to caller
        self._helper_callback = None


    def on_after_startup(self):
        self.imgproc = ImageProcessing(float(self._settings.get(["tray", "boxsize"])), int(self._settings.get(["camera", "bed", "binary_thresh"])), int(self._settings.get(["camera", "head", "binary_thresh"])))
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
                "rimsize": 1.0
            },
            "vacnozzle": {
                "x": 0,
                "y": 0,
                "z_pressure": 0,
                "extruder_nr": 2,
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
                    "pxPerMM": 50.0,
                    "path": "",
                    "binary_thresh": 150,
                    "grabScriptPath": ""
                },
                "bed": {
                    "x": 0,
                    "y": 0,
                    "z": 0,
                    "pxPerMM": 50.0,
                    "path": "",
                    "binary_thresh": 150,
                    "grabScriptPath": ""
                },
                "image_logging": False
            }
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
                "js/smdTray.js",
                "js/settings.js"]
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
                        f = open(imagePath,"r")
                        result = flask.jsonify(src="data:image/" + os.path.splitext(imagePath)[1] + ";base64,"+base64.b64encode(bytes(f.read())))
                    except IOError:
                        result = flask.jsonify(error="Unable to open Image after fetching. Image path: " + imagePath)
                else:
                    result = flask.jsonify(error="Unable to fetch image. Check octoprint log for details.")
        return flask.make_response(result, 200)

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
                    #TODO: validate part informations against tray
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
    """
    def hook_gcode_queuing(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if "M361" in cmd:
            if self._state == self.STATE_NONE:
                self._state = self.STATE_PICK
                command = re.search("P\d*", cmd).group() #strip the M361
                self._currentPart = int(command[1:])

                self._logger.info( "Received M361 command to place part: " + str(self._currentPart))

                # pause running printjob to prevent octoprint from sending new commands from the gcode file during the interactive PnP process
                if self._printer.is_printing():
                    self._printer.pause_print()

                self._updateUI("OPERATION", "pick")

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
                self.imgproc = ImageProcessing(float(self._settings.get(["tray", "boxsize"])), int(self._settings.get(["camera", "bed", "binary_thresh"])), int(self._settings.get(["camera", "head", "binary_thresh"])))

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
                if self._printer.is_paused():
                    self._printer.resume_print()

                return (None,) # suppress command

        # handle camera positioning for external request (helper function)
        if "M362 OctoPNP_camera_external" in cmd:
            result = self._grabImages("HEAD")

            # the current printjob is resumed and octoPNP is set into default state
            # before returning the obtained image by callback to allow recursive executions
            # of the camera_helper by 3. party plugins (the camera helper is triggered from within the callback method).

            # resume paused printjob into normal operation
            if self._printer.is_paused():
                self._printer.resume_print

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
        # switch to pimary extruder, since the head camera is relative to this extruder and the offset to PNP nozzle might not be known (firmware offset)
        self._printer.commands("T0")
        # move camera to part position
        tray_offset = self._getTrayPosFromPartNr(partnr) # get box position on tray
        camera_offset = [tray_offset[0]-float(self._settings.get(["camera", "head", "x"])), tray_offset[1]-float(self._settings.get(["camera", "head", "y"])), float(self._settings.get(["camera", "head", "z"])) + tray_offset[2]]
        cmd = "G1 X" + str(camera_offset[0]) + " Y" + str(camera_offset[1]) + " F" + str(self.FEEDRATE)
        self._logger.info("Move camera to: " + cmd)
        self._printer.commands("G91") # relative positioning
        self._printer.commands("G1 Z5 F" + str(self.FEEDRATE)) # lift printhead
        self._printer.commands("G90") # absolute positioning
        self._printer.commands(cmd)
        self._printer.commands("G1 Z" + str(camera_offset[2]) + " F" + str(self.FEEDRATE)) # lower printhead


    def _pickPart(self, partnr):
        # wait n seconds to make sure cameras are ready
        #time.sleep(1) # is that necessary?

        part_offset = [0, 0]

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

        tray_offset = self._getTrayPosFromPartNr(partnr)
        vacuum_dest = [tray_offset[0]+part_offset[0]-float(self._settings.get(["vacnozzle", "x"])),\
                         tray_offset[1]+part_offset[1]-float(self._settings.get(["vacnozzle", "y"])),\
                         tray_offset[2]+self.smdparts.getPartHeight(partnr)-float(self._settings.get(["vacnozzle", "z_pressure"]))]

        # move vac nozzle to part and pick
        self._printer.commands("T" + str(self._settings.get(["vacnozzle", "extruder_nr"])))
        cmd = "G1 X" + str(vacuum_dest[0]) + " Y" + str(vacuum_dest[1]) + " F" + str(self.FEEDRATE)
        self._printer.commands(cmd)
        self._printer.commands("G1 Z" + str(vacuum_dest[2]+10))
        self._releaseVacuum()
        self._lowerVacuumNozzle()
        self._printer.commands("G1 Z" + str(vacuum_dest[2]) + "F1000")
        self._gripVacuum()
        self._printer.commands("G4 S1")
        self._printer.commands("G1 Z" + str(vacuum_dest[2]+5) + "F1000")

        # move to bed camera
        vacuum_dest = [float(self._settings.get(["camera", "bed", "x"]))-float(self._settings.get(["vacnozzle", "x"])),\
                       float(self._settings.get(["camera", "bed", "y"]))-float(self._settings.get(["vacnozzle", "y"])),\
                       float(self._settings.get(["camera", "bed", "z"]))+self.smdparts.getPartHeight(partnr)]

        self._printer.commands("G1 X" + str(vacuum_dest[0]) + " Y" + str(vacuum_dest[1]) + " F"  + str(self.FEEDRATE))
        self._printer.commands("G1 Z" + str(vacuum_dest[2]) + " F"  + str(self.FEEDRATE))
        self._logger.info("Moving to bed camera: %s", cmd)

    def _alignPart(self, partnr):
        orientation_offset = 0

        # find destination at the object
        destination = self.smdparts.getPartDestination(partnr)

        # take picture
        self._logger.info("Taking bed align picture NOW")
        bedPath = self._settings.get(["camera", "bed", "path"])
        if self._grabImages("BED"):
            #update UI
            self._updateUI("BEDIMAGE", bedPath)

            # get rotation offset
            orientation_offset = self.imgproc.getPartOrientation(bedPath, float(self._settings.get(["camera", "bed", "pxPerMM"])), 0)
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
        self._printer.commands("G1 E" + str(destination[3]-orientation_offset) + " F" + str(self.FEEDRATE))

    def _placePart(self, partnr):
        displacement = [0, 0]

        # find destination at the object
        destination = self.smdparts.getPartDestination(partnr)

        # take picture to find part offset
        self._logger.info("Taking bed offset picture NOW")
        bedPath = self._settings.get(["camera", "bed", "path"])
        if self._grabImages("BED"):

            orientation_offset = self.imgproc.getPartOrientation(bedPath, float(self._settings.get(["camera", "bed", "pxPerMM"])), destination[3])
            if not orientation_offset:
                self._updateUI("ERROR", self.imgproc.getLastErrorMessage())
                orientation_offset = 0.0

            displacement = self.imgproc.getPartPosition(bedPath, float(self._settings.get(["camera", "bed", "pxPerMM"])))
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
            self._printer.commands("G1 E" + str(-orientation_offset) + " F" + str(self.FEEDRATE))
            # wait a second to execute the rotation
            time.sleep(2)
            # take another image for UI
            if self._grabImages("BED"):

                displacement = self.imgproc.getPartPosition(bedPath, float(self._settings.get(["camera", "bed", "pxPerMM"])))
                #update UI
                self._updateUI("BEDIMAGE", self.imgproc.getLastSavedImagePath())

                # Log image for debugging and documentation
                if self._settings.get(["camera", "image_logging"]): self._saveDebugImage(bedPath)
            else:
                self._updateUI("ERROR", "Camera not ready")

        # move to destination
        dest_z = destination[2]+self.smdparts.getPartHeight(partnr)-float(self._settings.get(["vacnozzle", "z_pressure"]))
        cmd = "G1 X" + str(destination[0]-float(self._settings.get(["vacnozzle", "x"]))+displacement[0]) \
              + " Y" + str(destination[1]-float(self._settings.get(["vacnozzle", "y"]))+displacement[1]) \
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
        grabScript = "";
        if(camera == "HEAD"):
            grabScript = self._settings.get(["camera", "head", "grabScriptPath"])
        if(camera == "BED"):
            grabScript = self._settings.get(["camera", "bed", "grabScriptPath"])
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
                for partId in partIds:
                    partArray.append(
                        dict(
                            id = partId,
                            name = self.smdparts.getPartName(partId),
                            partPosition = self.smdparts.getPartPosition(partId),
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
            f = open(parameter,"r")
            data = dict(
                src = "data:image/" + os.path.splitext(parameter)[1] + ";base64,"+base64.b64encode(bytes(f.read()))
            )

        message = dict(
            event=event,
            data=data
        )
        self._pluginManager.send_plugin_message("OctoPNP", message)



    # Helper function to provide camera access to other plugins.
    # Returns resolution for 'camera' (HEAD or BED).
    def _helper_get_head_camera_pxPerMM(self, camera):
        if camera == "HEAD":
            return self._settings.get(["camera", "head", "pxPerMM"])
        if camera == "BED":
            return self._settings.get(["camera", "bed", "pxPerMM"])
        return 0.0


    # Helper function to provide camera access to other plugins.
    # Moves printhead with camera to given x/y coordinates, takes
    # a picture and returns by invoking the callback function.
    # Can only be used for the head camera, since bed camera is fixed and can't be moved to a x/y coordinate.
    #
    # adjust_focus: add camera focus distance to current z position.
    # Can be disabled to take multiple shots without moving the z-axis
    def _helper_get_head_camera_image_xy(self, x, y, callback, adjust_focus=True):
        result = False;

        self._logger.info("Trying to take image at pos [" + str(x) + ":" + str(y) + "] for external plugin")

        if self._state == self.STATE_NONE:
            self._state = self.STATE_EXTERNAL
            result = True
            if self._printer.is_printing(): # interrupt running printjobs to prevent octoprint from sending further gcode lines from the file
                self._printer.pause_print()


            # store callback
            self._helper_callback = callback

            target_position = [x-float(self._settings.get(["camera", "head", "x"])), y-float(self._settings.get(["camera", "head", "y"])), float(self._settings.get(["camera", "head", "z"]))]
            cmd = "G1 X" + str(target_position[0]) + " Y" + str(target_position[1]) + " F" + str(self.FEEDRATE)
            if adjust_focus:
                self._printer.commands("G91") # relative positioning
                self._printer.commands("G1 Z" + str(target_position[2]) + " F" + str(self.FEEDRATE)) # lift printhead
                self._printer.commands("G90") # absolute positioning
            self._printer.commands(cmd)

            self._printer.commands("M400")
            self._printer.commands("G4 P1")
            self._printer.commands("M400")
            self._printer.commands("M362 OctoPNP_camera_external")

        else:
            self._logger.info("Abort, OctoPNP is busy (not in state NONE, current state: " + str(self._state) + ")")

        return result
