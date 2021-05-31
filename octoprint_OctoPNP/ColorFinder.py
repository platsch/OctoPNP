#!/usr/bin/python
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

import sys
import cv2
import numpy as np
import time


if (len(sys.argv) < 2):
    print("Usage: ColorFinder.py filename")
else:
    print("Press [ESC] to exit...")
    filename = sys.argv[1]

    # open image file
    img=cv2.imread(filename,cv2.IMREAD_COLOR)
    h,w,c = np.shape(img)

    blur_img=cv2.blur(img, (5,5))
    hsv = cv2.cvtColor(blur_img, cv2.COLOR_BGR2HSV)

    # remove the corners from mask since they are prone to illumination problems
    circle_mask = np.zeros((h, w), np.uint8)
    circle_mask[:, :] = 255
    cv2.circle(circle_mask,(int(w/2), int(h/2)), int(min(w/2, h/2)), 0, -1)

    lower_color = np.array([22,28,26])
    upper_color = np.array([103,255,255])

    def nothing(x):
        pass
    cv2.namedWindow('image')
    cv2.createTrackbar('H_low','image',lower_color[0],179,nothing)
    cv2.createTrackbar('H_up','image',upper_color[0],179,nothing)
    cv2.createTrackbar('S_low','image',lower_color[1],255,nothing)
    cv2.createTrackbar('S_up','image',upper_color[1],255,nothing)
    cv2.createTrackbar('V_low','image',lower_color[2],255,nothing)
    cv2.createTrackbar('V_up','image',upper_color[2],255,nothing)

    while(1):
        k = cv2.waitKey(1) & 0xFF
        if k == 27:
            break
        # get current positions of four trackbars
        lower_color = np.array([cv2.getTrackbarPos('H_low','image'),cv2.getTrackbarPos('S_low','image'),cv2.getTrackbarPos('V_low','image')])
        upper_color = np.array([cv2.getTrackbarPos('H_up','image'),cv2.getTrackbarPos('S_up','image'),cv2.getTrackbarPos('V_up','image')])

        # create binary mask by finding background color range
        mask = cv2.inRange(hsv, lower_color, upper_color)
        mask = cv2.bitwise_or(mask,circle_mask)
        cv2.imshow('image',mask)
        time.sleep(0.01)

    cv2.destroyAllWindows()
    print("Copy this color to your code:")
    print("self.lower_mask_color = np.array([" + str(lower_color[0]) + "," + str(lower_color[1]) + "," + str(lower_color[2]) + "])")
    print("self.upper_mask_color = np.array([" + str(upper_color[0]) + "," + str(upper_color[1]) + "," + str(upper_color[2]) + "])")
