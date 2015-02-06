# coding=utf-8
from __future__ import absolute_import

import xml.etree.ElementTree as ET

class SmdParts():

	def __init__(self):
		self._et = None
		pass

	def load(self, xmlstring):
		self._et = ET.fromstring(xmlstring)

	def getPartCount(self):
		pass

	def getPartPosition(self, partnr):
		pass

	def _parse(self, file):
		pass