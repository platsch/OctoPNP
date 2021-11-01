# coding=utf-8
from __future__ import absolute_import

__author__ = "Florens Wasserfall <wasserfall@kalanka.de>"
__license__ = "GNU Affero General Public License http://www.gnu.org/licenses/agpl.html"


import xml.etree.ElementTree as ET


class SmdParts:

    def __init__(self):
        self.__et = None
        self.__positions = {}

    def load(self, xmlstring):
        self.__et = ET.fromstring(xmlstring)
        msg = self.__sanitize()
        if msg == "":
            # init col and row dict with -1 to indicate no position assigned yet
            #TODO: maybe a map call is possible?
            self.__positions = {}
            for part_id in self.getPartIds():
                self.__positions[part_id] = {"row": -1, "col": -1}
            return msg
        self.unload()
        return msg

    def unload(self):
        self.__et = None

    def isFileLoaded(self):
        return bool(self.__et is not None)

    def getPartCount(self):
        return len(self.__et.findall("./part"))

    # returns a list of all available parts
    def getPartIds(self):
        #TODO: maybe a map call is possible?
        result = []
        for elem in self.__et.findall("./part"):
            result.append(int(elem.get("id")))
        return result

    # set position of this part on tray. Returns true if this part exists, false otherwise
    def setPartPosition(self, partnr, row, col):
        if partnr in self.__positions:
            self.__positions[partnr]["row"] = row
            self.__positions[partnr]["col"] = col
            return True
        return False

    # return a dict with row and col of the box this part is supposed to be in
    def getPartPosition(self, partnr):
        if partnr in self.__positions:
            return self.__positions[partnr]
        return {"row": -1, "col": -1}

    def getPartName(self, partnr):
        return self.__et.find("./part[@id='" + str(partnr) + "']").get("name")

    def getPartHeight(self, partnr):
        return float(
            self.__et.find("./part[@id='" + str(partnr) + "']/size").get("height")
        )

    def getPartShape(self, partnr):
        result = []
        if self.__et.find("./part[@id='" + str(partnr) + "']/shape") is not None:
            #TODO: maybe a map call is possible?
            for elem in self.__et.find("./part[@id='" + str(partnr) + "']/shape"):
                result.append([float(elem.get("x")), float(elem.get("y"))])
        return result

    def getPartPads(self, partnr):
        result = []
        if self.__et.find("./part[@id='" + str(partnr) + "']/pads") is not None:
            #TODO: maybe a map call is possible?
            for elem in self.__et.find("./part[@id='" + str(partnr) + "']/pads"):
                result.append(
                    [
                        float(elem.get("x1")),
                        float(elem.get("y1")),
                        float(elem.get("x2")),
                        float(elem.get("y2")),
                    ]
                )
        return result

    def getPartDestination(self, partnr):
        x = float(
            self.__et.find("./part[@id='" + str(partnr) + "']/destination").get("x")
        )
        y = float(
            self.__et.find("./part[@id='" + str(partnr) + "']/destination").get("y")
        )
        z = float(
            self.__et.find("./part[@id='" + str(partnr) + "']/destination").get("z")
        )
        orientation = self.__et.find(
                "./part[@id='" + str(partnr) + "']/destination"
                ).get("orientation")
        if orientation is None:
            orientation = 0
        return [x, y, z, float(orientation)]

    def __sanitize(self):
        # valid object?
        msg = self.__validate_object()

        # Iterate over parts
        for count, part in enumerate(self.__et.iter("part")):
            if not msg == "":
                break

            # id
            try:
                int(part.get("id"))
            except TypeError:
                msg = "Invalid or no id in part " + str(count+1)

            # sanitize part name
            if not part.get("name"):
                part.set("name", "part " + str(count+1))

            # box position
            if msg == "":
                msg = self.__sanitizeTag(part, "position", ["box"], int)

            # height
            if msg == "":
                msg = self.__sanitizeTag(part, "size", ["height"], float)

            # shape
            if msg == "":
                msg = self.__wrapper_sanitize_attribute(part, "shape", ["x", "y"], float)

            # pads
            if msg == "":
                msg = self.__wrapper_sanitize_attribute(
                    part, "pads", ["x1", "y1", "x2", "y2"], float
                )

            # destination
            if msg == "":
                msg = self.__sanitizeTag(
                        part, "destination", ["x", "y", "z", "orientation"], float
                    )

        return msg

    def __validate_object(self):
        msg = ""
        if self.__et.tag != "object":
            msg = "file contains XML data, but no valid <object>"
        # object name
        if not self.__et.attrib.get("name"):
            self.__et.set("name", "Object 1")
        return msg

    @classmethod
    def __wrapper_sanitize_attribute(cls, part, obj, attributes, validate):
        msg = ""
        if part.find(obj) is not None:
            for elem in part.find(obj):
                msg = cls.__sanitizeAttribute(
                    part, elem, attributes , validate
                )
                if not msg == "":
                    break
        return msg

    @classmethod
    def __sanitizeTag(cls, part, tag, attributes, validate):
        msg = "No Tag {0} in part {1} - {2}".format(
            tag, part.get("id"), part.get("name")
        )

        elem = part.find(tag)
        if elem is not None:
            msg = cls.__sanitizeAttribute(part, elem, attributes, validate)
        return msg

    @classmethod
    def __sanitizeAttribute(cls, part, elem, attributes, validate):
        msg = ""

        for attribute in attributes:
            try:
                validate(elem.get(attribute))
            except TypeError:
                msg = "Invalid or no attribute {0} in part {1} - {2}".format(
                    attribute, part.get("id"), part.get("name")
                )
                break

        return msg
