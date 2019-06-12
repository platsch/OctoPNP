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
        self.color_mask = ((22,28,26), (103,255,255)) # color_mask
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
        inputImage = cv2.imread(img_path)

        #---------<
        # Create a binarized image of the input containing only the areas within the
        # provided color mask (black)
        maskImageRaw = VisionPNP.createColorRangeMask(inputImage, self.color_mask)
        maskImage = np.array(maskImageRaw)

        #---------<
        # Extract bouding rect fom binarized mask image
        bRect = VisionPNP.findContainedRect(maskImage)

        #---------<
        # Crop the input image to the shape of the provided mask
        croppedImageRaw = VisionPNP.cropImageToRect(inputImage, bRect)
        croppedImage = np.array(croppedImageRaw)

        filename="/cropped_"+os.path.basename(self._img_path)
        finalcm_path=os.path.dirname(self._img_path)+filename
        cv2.imwrite(finalcm_path,croppedImage)

        if(croppedImage.any()):
            #---------<
            # Find the position of a single object inside the provided image
            position = VisionPNP.findShape(finalcm_path)

            left_x = bRect[2]
            right_x = bRect[2] + bRect[1]
            upper_y = bRect[3]
            lower_y = bRect[3] + bRect[0]


            if(position):
                # Calculate offset
                cm_x = position[0]
                cm_y = position[1]

                res_x = croppedImage.shape[1]
                res_y = croppedImage.shape[0]

                displacement_x=(cm_x-res_x/2)*self.box_size/res_x
                displacement_y=((res_y-cm_y)-res_y/2)*self.box_size/res_y
                if relative_to_camera:
                    #incorporate the position of the tray box in relation to the image
                    displacement_x += (left_x - (inputImage.shape[1]-right_x))/2 * self.box_size/res_x
                    displacement_y -= (upper_y - (inputImage.shape[0]-(lower_y)))/2 * self.box_size/res_y
                result = displacement_x,displacement_y

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

    def getPartOrientation(self,img_path, template_path, pxPerMM, offset=0):
        self._img_path = img_path
        result = False

        inputImage = cv2.imread(img_path)
        inputTemplate = cv2.imread(template_path)

        # Find orientation
        bestCandidate = VisionPNP.matchTemplate(inputImage, inputTemplate, self.color_mask, componentSize)
        candidateImage = VisionPNP.drawCandidate(inputImage, inputTemplate, bestCandidate)

        orientation = bestCandidate[3]

        if(orientation != False):
            orientation = orientation * (180 / math.pi)
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

        if self._interactive: cv2.imshow("contours",candidateImage)
        if self._interactive: cv2.waitKey(0)

        #save result as image for GUI
        filename="/orientation_"+os.path.basename(self._img_path)
        orientation_img_path=os.path.dirname(self._img_path)+filename
        cv2.imwrite(orientation_img_path, candidateImage)
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
        cleanedImageRaw = VisionPNP.binaryFromRange(inputImage, self.color_mask)
        cleanedImage = np.array(cleanedImageRaw)

        # Find center of mass
        center = VisionPNP.findShape(cleanedImage)

        if(center):
            cm_x = center[0]
            cm_y = center[1]
            res_x = inputImage.shape[1]
            res_y = inputImage.shape[0]

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
# INPUT: array for shape and pads, square resolution for template (default 200px)
# OUTPUT: template image (numpy array)

    def createTemplate(self, xmlShape, xmlPads, resolution=200):
      # create white template background
      templateImage = np.zeros((resolution,resolution,1),dtype=np.uint8)
      templateImage.fill(255)

      # convert arrays to numpy arrays
      shape = np.array(xmlShape, dtype=float)
      pads = np.array(xmlPads, dtype=float)

      # retrieve max value from coordinates
      maximum = self._getMaximum(shape, pads)

      # create polygon from shape
      shapePoints = []
      for pos in shape:
          p = self._toPixelPoint(resolution, maximum, (pos[0], pos[1]))
          shapePoints.append(p)

      # draw polygon
      pts = np.array(shapePoints, np.int32)
      cv2.fillPoly(templateImage,[pts],(0,0,0))

      # create rectangles from pads
      for pad in pads:
          # Convert template coordinates to pixel format
          p1 = self._toPixelPoint(resolution, maximum, (pad[0], pad[1]))
          p2 = self._toPixelPoint(resolution, maximum, (pad[2], pad[3]))
          # draw
          cv2.rectangle(templateImage, p1, p2, (0,0,0), -1)
      return templateImage

#==============================================================================
# Return maximum point from vector coordinates
    def _getMaximum(self, shape, pads):
        maxPosition = []
        # Maximum for shape
        maxPosition.append(np.amax(shape))
        maxPosition.append(abs(np.amin(shape)))
        # Maximum for pads
        maxPosition.append(np.amax(pads))
        maxPosition.append(abs(np.amin(pads)))
        # Overall maximum
        maxPosition = np.array(maxPosition, np.float)
        return np.amax(maxPosition)

#==============================================================================
# Converts XML vector coordinates to pixel coordinates
    def _toPixelPoint(self, resolution, maximum, point):
        return (int(resolution * ((point[0] + maximum) / (maximum * 2))),
                int(resolution * ((point[1] + maximum) / (maximum * 2))))

#==============================================================================
    def _saveImage(self, filename, img):
        img_path=os.path.dirname(self._img_path)+filename
        cv2.imwrite(img_path,img)
        return
