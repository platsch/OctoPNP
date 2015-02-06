# coding=utf-8
from __future__ import absolute_import

import xml.etree.ElementTree as ET

class SmdParts():

	def __init__(self):
		self._et = None
		pass

	def load(self, xmlstring):
		self._et = ET.fromstring(xmlstring)

		#print content for debug
		print "root tag: " + self._et.tag
		print "root attribute: "
		print self._et.attrib

		for child in self._et:
			print "child t, a: "
			print child.tag, child.attrib
			print "\n"

	def getPartCount(self):
		pass

	#return the nr of the box this part is supposed to be in
	def getPartPosition(self, partnr):
		return int(self._et.find("./part[@id='" + str(partnr) + "']/position").get("box"))


	def getPartDestination(self, partnr):
		pass