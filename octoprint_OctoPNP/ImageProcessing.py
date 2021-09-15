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
import os


class ImageProcessing:
    def __init__(self, box_size, bed_cam_binary_thresh, head_cam_binary_thresh):
        self.box_size = box_size
        self.bed_binary_thresh = bed_cam_binary_thresh
        self.head_binary_thresh = head_cam_binary_thresh
        # self.lower_mask_color = np.array([22,28,26]) # green default
        # self.upper_mask_color = np.array([103,255,255])
        self.lower_mask_color = np.array([0, 85, 76])
        self.upper_mask_color = np.array([100, 255, 255])
        self._img_path = ""
        self._last_saved_image_path = None
        self._last_error = ""
        self._interactive = False
        self._debug = True

    # Locates a part in a box. Box size must be given to constructor. Image must contain only
    # one box with white background.
    # Returns displacement with respect to the center of the box if a part is detected, False otherwise.
    # boolean relative_to_camera sets wether the offset should be relative to the box or to the camera.
    # ===================================================================================================
    def locatePartInBox(self, img_path, relative_to_camera):
        result = False

        self._img_path = img_path
        # open image file
        img = cv2.imread(img_path, cv2.IMREAD_COLOR)

        # detect box boundaries
        rotated_crop_rect = self._rotatedBoundingBox(
            img, self.head_binary_thresh, 0.6, 0.95
        )
        if rotated_crop_rect:
            rotated_box = cv2.boxPoints(rotated_crop_rect)

            left_x = int(min(rotated_box[0][0], rotated_box[1][0]))
            right_x = int(max(rotated_box[2][0], rotated_box[3][0]))
            upper_y = int(min(rotated_box[1][1], rotated_box[2][1]))
            lower_y = int(max(rotated_box[0][1], rotated_box[3][1]))

            # workaround for bounding boxes that are bigger then the image
            if left_x < 0:
                left_x = 0
            if upper_y < 0:
                upper_y = 0
            if right_x < 0:
                right_x = img.shape[1]
            if lower_y < 0:
                lower_y = img.shape[0]

            # Crop image
            img_crop = img[upper_y:lower_y, left_x:right_x]

            # now find part inside the box
            cm_rect = self._rotatedBoundingBox(
                img_crop, self.head_binary_thresh, 0.001, 0.7
            )
            if cm_rect:
                cm_x = cm_rect[0][0]
                cm_y = cm_rect[0][1]

                res_x = img_crop.shape[1]
                res_y = img_crop.shape[0]

                displacement_x = (cm_x - res_x / 2) * self.box_size / res_x
                displacement_y = ((res_y - cm_y) - res_y / 2) * self.box_size / res_y
                if relative_to_camera:
                    # incorporate the position of the tray box in relation to the image
                    displacement_x += (
                        (left_x - (img.shape[1] - right_x)) / 2 * self.box_size / res_x
                    )
                    displacement_y -= (
                        (upper_y - (img.shape[0] - (lower_y)))
                        / 2
                        * self.box_size
                        / res_y
                    )
                result = displacement_x, displacement_y

                # Generate result image and return
                cv2.circle(img_crop, (int(cm_x), int(cm_y)), 5, (0, 255, 0), -1)
                filename = "/finalcm_" + os.path.basename(self._img_path)
                finalcm_path = os.path.dirname(self._img_path) + filename
                cv2.imwrite(finalcm_path, img_crop)
                self._last_saved_image_path = finalcm_path

                if self._interactive:
                    cv2.imshow("Part in box: ", img_crop)
                if self._interactive:
                    cv2.waitKey(0)
            else:
                self._last_error = "Unable to find part in box"
        else:
            self._last_error = "Unable to locate box"

        return result

    # Get part orientation by computing a rotated bounding box around contours
    # and determining the main orientation of this box
    # Returns the angle of main edges relativ to the
    # next main axis [-45°:45°]
    def getPartOrientation(self, img_path, pxPerMM, offset=0):
        self._img_path = img_path
        result = False

        # open image file
        img = cv2.imread(img_path, cv2.IMREAD_COLOR)

        mask = self._maskBackground(img)

        # we should use actual object size here
        min_area_factor = pxPerMM ** 2 / (img.shape[1] * img.shape[0])  # 1mm²
        rect = self._rotatedBoundingBox(img, 50, 0.005, 0.7, mask)

        if rect:
            # draw rotated bounding box for visualization
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            cv2.drawContours(img, [box], 0, (0, 0, 255), 2)

            # compute rotation offset
            rotation = rect[2] - offset
            # normalize to positive PI range
            if rotation < 0:
                rotation = (rotation % -180) + 180

            rotation = rotation % 90
            result = -rotation if rotation < 45 else 90 - rotation

            if self._debug:
                print("Part deviation measured by bed camera: " + str(result))
        else:
            self._last_error = "Unable to locate part for finding the orientation"
            if self._debug:
                print(self._last_error)
            result = False

        if self._interactive:
            cv2.imshow("contours", img)
        if self._interactive:
            cv2.waitKey(0)

        # save result as image for GUI
        filename = "/orientation_" + os.path.basename(self._img_path)
        orientation_img_path = os.path.dirname(self._img_path) + filename
        cv2.imwrite(orientation_img_path, img)
        self._last_saved_image_path = orientation_img_path

        return result

    # Find the position of a (already rotated) part. Returns the offset between the
    # center of the image and the parts center of mass, 0,0 if no part is detected.
    # ==============================================================================
    def getPartPosition(self, img_path, pxPerMM):
        self._img_path = img_path
        result = False

        # open image file
        img = cv2.imread(img_path, cv2.IMREAD_COLOR)

        mask = self._maskBackground(img)

        res_x = img.shape[1]
        res_y = img.shape[0]

        # we should use actual object size here
        min_area_factor = pxPerMM ** 2 / (res_x * res_y)  # 1mm²
        rect = self._rotatedBoundingBox(img, 50, min_area_factor, 0.7, mask)

        if rect:
            cm_x = rect[0][0]
            cm_y = rect[0][1]

            displacement_x = (cm_x - res_x / 2) / pxPerMM
            displacement_y = ((res_y - cm_y) - res_y / 2) / pxPerMM
            result = [displacement_x, -displacement_y]
        else:
            self._last_error = "Unable to locate part for correcting the position"
            if self._debug:
                print(self._last_error)
            result = False

        # write image for UI
        cv2.circle(img, (int(cm_x), int(cm_y)), 5, (0, 255, 0), -1)
        filename = "/final_" + os.path.basename(self._img_path)
        final_img_path = os.path.dirname(self._img_path) + filename
        cv2.imwrite(final_img_path, img)
        self._last_saved_image_path = final_img_path

        if self._interactive:
            cv2.imshow("Center of Mass", img)
        if self._interactive:
            cv2.waitKey(0)

        return result

    # ==============================================================================
    def getLastSavedImagePath(self):
        if self._last_saved_image_path:
            return self._last_saved_image_path
        else:
            return False

    # ==============================================================================
    def getLastErrorMessage(self):
        return self._last_error

    # ==============================================================================
    def _rotatedBoundingBox(
        self, img, binary_thresh, min_area_factor, max_area_factor, binary_img=()
    ):
        result = False

        if len(binary_img) == 0:
            # convert image to grey and blur
            gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray_img = cv2.blur(gray_img, (3, 3))
            ret, binary_img = cv2.threshold(
                gray_img, binary_thresh, 255, cv2.THRESH_BINARY
            )

        # depending on the OpenCV Version findContours returns 2 or 3 objects...
        # contours, hierarchy = cv2.findContours(binary_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE, (0, 0))
        contours = cv2.findContours(
            binary_img, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE, offset=(0, 0)
        )[0]

        # cv2.drawContours(img, contours, -1, (0,255,0), 3) # draw basic contours

        minArea = (
            binary_img.shape[0] * binary_img.shape[1] * min_area_factor
        )  # how to find a better value??? input from part description?
        maxArea = (
            binary_img.shape[0] * binary_img.shape[1] * max_area_factor
        )  # Y*X | don't detect full image

        rectPoints = []

        for contour in contours:
            rect = cv2.minAreaRect(contour)
            rectArea = rect[1][0] * rect[1][1]
            if rectArea > minArea and rectArea < maxArea:
                box = cv2.boxPoints(rect)
                for point in box:
                    rectPoints.append(np.array(point, dtype=np.int32))
                if self._interactive:
                    box = np.int0(box)
                if self._interactive:
                    cv2.drawContours(img, [box], 0, (0, 0, 255), 2)
            # cv2.imshow("contours",binary_img)
            # cv2.waitKey(0)
        if self._interactive:
            cv2.imshow("Binarized image", binary_img)
        if self._interactive:
            cv2.waitKey(0)
        if self._interactive:
            cv2.imshow("contours", img)
        if self._interactive:
            cv2.waitKey(0)

        if len(rectPoints) >= 4:
            rectArray = np.array(rectPoints)
            rect = cv2.minAreaRect(rectArray)

            # draw rotated bounding box for visualization
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            cv2.drawContours(img, [box], 0, (0, 0, 255), 2)
            result = rect
        else:
            self._last_error = "Unable to find contour in image"

        return result

    # Compute a binary image / mask by removing all pixels in the given color range
    # mask_corners: remove all pixels outside a circle touching the image boundaries
    #      to crop badly illuminated corners
    # ==============================================================================
    def _maskBackground(self, img, mask_corners=True):
        h, w, c = np.shape(img)

        blur_img = cv2.blur(img, (5, 5))
        hsv = cv2.cvtColor(blur_img, cv2.COLOR_BGR2HSV)

        lower_color = np.array([22, 28, 26])
        upper_color = np.array([103, 255, 255])

        # create binary mask by finding background color range
        mask = cv2.inRange(hsv, self.lower_mask_color, self.upper_mask_color)
        # remove the corners from mask since they are prone to illumination problems
        if mask_corners:
            circle_mask = np.zeros((h, w), np.uint8)
            circle_mask[:, :] = 255
            cv2.circle(
                circle_mask,
                (int(w / 2), int(h / 2)),
                min(int(w / 2), int(h / 2)),
                0,
                -1,
            )
            mask = cv2.bitwise_or(mask, circle_mask)
        # invert mask to get white objects on black background
        # inverse_mask = 255 - mask

        if self._interactive:
            cv2.imshow("binary mask", mask)
        if self._interactive:
            cv2.waitKey(0)

        return mask
