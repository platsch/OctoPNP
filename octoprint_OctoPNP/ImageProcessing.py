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

import cv2
import numpy as np
import math
import os
import shutil
import VisionPNP

class ImageProcessing:

    def __init__(self, box_size, color_mask):
        self.box_size=box_size
        self.color_mask = color_mask
        self._img_path = ""
        self._last_saved_image_path = None
        self._last_error = ""
        self._interactive=False
        self._debug = True


# Locates a part in a box. Box size must be given to constructor. Image must contain only
# one box with white background.
# Returns displacement with respect to the center of the box if a part is detected, False otherwise.
# boolean relative_to_camera sets wether the offset should be relative to the box or to the camera.
#===================================================================================================
    def locatePartInBox(self, img_path, relative_to_camera):
        result = False

        self._img_path = img_path
        cv2.imread(img_path, inputImage)

        #---------<
        # Create a binarized image of the input containing only the areas within the
        # provided color mask (black)
        maskImageRaw = VisionPNP.createColorRangeMask(inputImage, self.color_mask)
        maskImage = np.array(maskImageRaw)

        #---------<
        # Crop the input image to the shape of the provided mask
        croppedImageRaw = VisionPNP.cropImageToMask(headCamImage, maskImageConv)
        croppedImage = np.array(croppedImageRaw)

        if(croppedImage):
            #---------<
            # Find the position of a single object inside the provided image
            position = VisionPNP.findShape(croppedImage)
            print(position)

            if(position):
#---------< START TODO
# IDEA: Either return object containing cropped image AND x/y offset or just the shape and crop in python.
                # Calculate offset
                cm_x = cm_rect[0][0]
                cm_y = cm_rect[0][1]

                res_x = croppedImage.shape[1]
                res_y = croppedImage.shape[0]

                displacement_x=(cm_x-res_x/2)*self.box_size/res_x
                displacement_y=((res_y-cm_y)-res_y/2)*self.box_size/res_y
                if relative_to_camera:
                    #incorporate the position of the tray box in relation to the image
                    displacement_x += (left_x - (img.shape[1]-right_x))/2 * self.box_size/res_x
                    displacement_y -= (upper_y - (img.shape[0]-(lower_y)))/2 * self.box_size/res_y
                result = displacement_x,displacement_y
#---------< END TODO

                # Generate result image and return
                cv2.circle(croppedImage,(position[0], position[1]), 4, (0,0,255), -1)
                filename="/finalcm_"+os.path.basename(self._img_path)
                finalcm_path=os.path.dirname(self._img_path)+filename
                cv2.imwrite(finalcm_path,croppedImage)
                self._last_saved_image_path = finalcm_path

                if self._interactive: cv2.imshow("Part in box: ",croppedImage)
                if self._interactive: cv2.waitKey(0)
            else:
                self._last_error = "Unable to find part in box"
        else:
            self._last_error = "Unable to locate box"
        return result


# Get part orientation by computing a rotated bounding box around contours
# and determining the main orientation of this box
# Returns the angle of main edges relativ to the
# next main axis [-45°:45°]
    def getPartOrientation(self,img_path, template_path, pxPerMM, offset=0):
        self._img_path = img_path
        result = False

        inputImage = cv2.imread(img_path)

        # Find orientation
        orientation = VisionPNP.matchTemplate(img_path, template_path, self.color_mask)

        if(orientation):
            # compute rotation offset
            rotation = orientation + offset
            # normalize to positive PI range
            if rotation < 0:
                rotation = (rotation % -180) + 180

            rotation = rotation % 90
            result = -rotation if rotation < 45 else 90-rotation

            if self._debug: print "Part deviation measured by bed camera: " + str(result)
        else:
            if self._debug: print "Unable to locate part for finding the orientation"
            self._last_error = "Unable to locate part for finding the orientation"
            result = False

        if self._interactive: cv2.imshow("contours",img)
        if self._interactive: cv2.waitKey(0)

        #save result as image for GUI
        filename="/orientation_"+os.path.basename(self._img_path)
        orientation_img_path=os.path.dirname(self._img_path)+filename
        cv2.imwrite(orientation_img_path, inputImage)
        self._last_saved_image_path = orientation_img_path

        return result


# Find the position of a (already rotated) part. Returns the offset between the
# center of the image and the parts center of mass, 0,0 if no part is detected.
#==============================================================================
    def getPartPosition(self, img_path, pxPerMM):
        self._img_path = img_path
        result = False

        # open image file
        inputImage=cv2.imread(img_path)

        # Clean green background
        cleanedImageRaw = VisionPNP.removeColorRange(inputImage, maskValues)
        cleanedImage = np.array(cleanedImageRaw)

        # Find center of mass
        center = VisionPNP.findShape(cleanedImage)

        if(center):
            cm_x = center[0]
            cm_y = center[1]

            displacement_x=(cm_x-res_x/2)/pxPerMM
            displacement_y=((res_y-cm_y)-res_y/2)/pxPerMM
            result = [displacement_x, -displacement_y]
            cv2.circle(inputImage,(center[0], center[1]), 4, (0,0,255), -1)
        else:
            if self._debug: print "Unable to locate part for correcting the position"
            self._last_error = "Unable to locate part for correcting the position"
            result = False

        # write image for UI
        filename="/final_"+os.path.basename(self._img_path)
        final_img_path=os.path.dirname(self._img_path)+filename
        cv2.imwrite(final_img_path,inputImage)
        self._last_saved_image_path = final_img_path

        if self._interactive: cv2.imshow("Center of Mass",img)
        if self._interactive: cv2.waitKey(0)

        return result

#==============================================================================
    def getColorRange(self, img_path):
      return VisionPNP.getHSVColorRange(img_path)
#==============================================================================
    def getLastSavedImagePath(self):
        if self._last_saved_image_path:
            return self._last_saved_image_path
        else:
            return False

#==============================================================================
    def getLastErrorMessage(self):
        return self._last_error

#==============================================================================
    def _saveImage(self, filename, img):
        img_path=os.path.dirname(self._img_path)+filename
        cv2.imwrite(img_path,img)
        return