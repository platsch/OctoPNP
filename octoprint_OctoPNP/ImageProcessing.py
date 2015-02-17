# -*- coding: utf-8 -*-
"""
Created on Tue Feb 17 02:12:51 2015

@author: soubarna
"""

import cv2
import numpy as np
#import scipy.signal as sig
#from matplotlib import pyplot as plt

class ImageProcessing:
        
    def __init__(self,img_input):
        self.img=img_input
    

    def boundary_detect(self):
        img_bkp=self.img.copy()
        curr_img=self.img
        # Converting Colorspace : BGR to HSV
        hsv = cv2.cvtColor(curr_img, cv2.COLOR_BGR2HSV)
        
        # Extracting Green Channel
        green = np.uint8([[[0,255,0 ]]])
        hsv_green = cv2.cvtColor(green,cv2.COLOR_BGR2HSV)
        lower_green=np.array([hsv_green[0][0][0]-40,100,100])
        upper_green=np.array([hsv_green[0][0][0]+40,255,255])
        
        # Threshold the HSV image to get only green colors
        mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # Bitwise-AND mask and original image
        res = cv2.bitwise_and(curr_img,curr_img, mask= mask)
    
        #Show Images
        cv2.imshow('Green Channel',res)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
               
        #Find Lines
        
        # Converting Image to Gray Scale
        gray_img=cv2.cvtColor(cv2.cvtColor(res,cv2.COLOR_HSV2BGR),cv2.COLOR_BGR2GRAY)
        
        # Smoothing Image
        gray_img = cv2.GaussianBlur(gray_img, (15, 15), 0)
        
        # Invert Image 
        ret,thresh = cv2.threshold(gray_img,0,255,cv2.THRESH_BINARY_INV)
        cv2.imshow('Inverted',thresh)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
        # Finding Contours with Max Area
        contours, hierarchy = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
        print "number of contours detected", len(contours)
        
        cnt=0
        maxArea=0
        flag=0
        maxArea=0
        for i in contours:
            currArea=cv2.contourArea(i)
            if currArea > 0.0:
                if currArea>maxArea:
                    maxArea=currArea
                    flag=cnt
            cnt=cnt+1
        
        # Drawing the contour and the bounding rectangle
        cv2.drawContours(curr_img, contours, flag, (0,0,255), 3)
        x,y,w,h = cv2.boundingRect(contours[flag])
        
        cv2.rectangle(curr_img,(x,y),(x+w,y+h),(255,0,0),2)
        
        print "rectangle width",w
        print "rectangle height",h
        # Show Image
        cv2.imshow("Contours",curr_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        #img1=img
        img_crop=img_bkp[x:x+w-1,y:y+h-1]
        #cv2.imwrite("cropped_output.jpg",img1)
        return img_crop
        
    def center_of_mass(crop_img):
        img_bkp=crop_img.copy()
        
       
        # Finding contours
        ret,thresh = cv2.threshold(crop_img,50,255,cv2.THRESH_BINARY_INV)
        cv2.imshow("threshold",thresh)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        
        contours, hierarchy = cv2.findContours(thresh,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        print "number of contours", len(contours)
    
        # Finding the contour with the max area
        cnt=0
        maxArea=0
        flag=0
        
        for i in contours:
            currArea=cv2.contourArea(i)
            if currArea > 0.0:
                
                if currArea>maxArea:
                    maxArea=currArea
                    flag=cnt
            cnt=cnt+1
        #==============================================================================
        # Calculating center of mass for the max area 
        #==============================================================================
        M = cv2.moments(contours[flag])
        cx1 = int(M['m10']/M['m00'])
        cy1 = int(M['m01']/M['m00'])
        cv2.circle(img_bkp,(cx1,cy1), 5, (255,0,0), -1)
        cv2.drawContours(img_bkp, contours, -1, (0,255,0), 3)
        
        cv2.imshow("Contours",img_bkp)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        print "Center of Mass : ",cx1,cy1
        return cx1,cy1
    
