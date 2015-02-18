# -*- coding: utf-8 -*-
"""
Created on Tue Feb 17 02:12:51 2015

@author: soubarna
"""

import cv2
import numpy as np

from subprocess import call
import shutil
import os
#import scipy.signal as sig
#from matplotlib import pyplot as plt

class ImageProcessing:

	def __init__(self,img_path,box_size):
		print "IP: ",img_path
		self.img_path = img_path
		self.box_size=box_size

	def get_cm(self):
		# open image file
		grabScript = os.path.dirname(os.path.realpath(__file__)) + "/cameras/pylon/grab.sh"
		if call([grabScript]) != 0:
			print "ERROR: camera not ready!"
			return 0, 0
		img=cv2.imread(self.img_path,cv2.IMREAD_COLOR)

		# make a copy of the file for later inspection
		shutil.copyfile(self.img_path, '/home/wasserfall/OctoPNP.tiff')

		#detect boundary and crop
		crop_image=self.boundaryDetect(img)
		#Get the center of mass
		gray_img=cv2.cvtColor(crop_image,cv2.COLOR_BGR2GRAY)
		cmx,cmy=self.centerofMass(gray_img)
		#return the displacement
		print "Calculating Displacement..."
		print "shape of cropped image",np.shape(crop_image)
		n_rows=crop_image.shape[0]
		n_cols=crop_image.shape[1]
		displacement_x=(cmx-n_rows/2)*self.box_size/n_rows
		displacement_y=((n_cols-cmy)-n_cols/2)*self.box_size/n_cols
		
		#cmx=200
		#cmy=200
		return displacement_x,displacement_y
	
	def boundaryDetect(self,img):
		img_bkp=img.copy()
		# Converting Colorspace : BGR to HSV
		hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
		
		# Extracting Green Channel
		green = np.uint8([[[0,255,0 ]]])
		hsv_green = cv2.cvtColor(green,cv2.COLOR_BGR2HSV)
		lower_green=np.array([hsv_green[0][0][0]-40,100,100])
		upper_green=np.array([hsv_green[0][0][0]+40,255,255])
		
		# Threshold the HSV image to get only green colors
		mask = cv2.inRange(hsv, lower_green, upper_green)
		
		# Bitwise-AND mask and original image
		res = cv2.bitwise_and(img,img, mask= mask)
		
		#Show Images
#		cv2.imshow('Green Channel',res)
#		cv2.waitKey(0)
#		cv2.destroyAllWindows()
		
			   
		#Find Lines
		
		# Converting Image to Gray Scale
		gray_img=cv2.cvtColor(cv2.cvtColor(res,cv2.COLOR_HSV2BGR),cv2.COLOR_BGR2GRAY)
		
		# Smoothing Image
		gray_img = cv2.GaussianBlur(gray_img, (15, 15), 0)
		
		# Invert Image 
		ret,thresh = cv2.threshold(gray_img,0,255,cv2.THRESH_BINARY_INV)
#		cv2.imshow('Inverted',thresh)
#		cv2.waitKey(0)
#		cv2.destroyAllWindows()
		
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
		cv2.drawContours(img, contours, flag, (0,0,255), 3)
		x,y,w,h = cv2.boundingRect(contours[flag])
		
		cv2.rectangle(img,(x,y),(x+w,y+h),(255,0,0),2)
		
		print "rectangle width",w
		print "rectangle height",h
		# Show Image
#		cv2.imshow("Contours",img)
#		cv2.waitKey(0)
#		cv2.destroyAllWindows()
		#img1=img
		img_crop=img_bkp[x:x+w-1,y:y+h-1]
		#cv2.imwrite("cropped_output.jpg",img1)
		return img_crop
	
	def centerofMass(self,crop_img):
		img_bkp=crop_img.copy()
		
		
		# Finding contours
		ret,thresh = cv2.threshold(crop_img,50,255,cv2.THRESH_BINARY_INV)
#		cv2.imshow("threshold",thresh)
#		cv2.waitKey(0)
#		cv2.destroyAllWindows()
		
		
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
		cx1 = float(M['m10']/M['m00'])
		cy1 = float(M['m01']/M['m00'])
#		cv2.circle(img_bkp,(cx1,cy1), 5, (255,0,0), -1)
#		cv2.drawContours(img_bkp, contours, -1, (0,255,0), 3)
		
#		cv2.imshow("Contours",img_bkp)
#		cv2.waitKey(0)
#		cv2.destroyAllWindows()
		print "Center of Mass : ",cx1,cy1
		return cx1,cy1
		
