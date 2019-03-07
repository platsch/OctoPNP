/*
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
    along with Repetier-Firmware.  If not, see <http://www.gnu.org/licenses/>.

    Main author: Florens Wasserfall <wasserfall@kalanka.de>
*/


// This is a configuration class to set pixel data format, Image AOI, exposure time and packet size for network transmission.

#ifndef INCLUDED_CAMERACONFIGURATION_H_00104928
#define INCLUDED_CAMERACONFIGURATION_H_00104928

#include <pylon/ConfigurationEventHandler.h>
#include <nlohmann/json.hpp>

namespace Pylon {
  class CInstantCamera;
}
class CCameraConfiguration : public Pylon::CConfigurationEventHandler {
public:
  CCameraConfiguration(json config) {
    this->config = config;
  }

  void OnOpened( Pylon::CInstantCamera& camera) {
    try {
      // Allow all the names in the namespace GenApi to be used without qualification.
      using namespace GenApi;

      // Get the camera control object.
      INodeMap &control = camera.GetNodeMap();

      // Get the parameters for setting the image area of interest (Image AOI).
      const CIntegerPtr width = control.GetNode("Width");
      const CIntegerPtr height = control.GetNode("Height");
      const CIntegerPtr offsetX = control.GetNode("OffsetX");
      const CIntegerPtr offsetY = control.GetNode("OffsetY");

      width->SetValue(this->config["imageSize"]);
      height->SetValue(this->config["imageSize"]);

      uint32_t tmp_offset = 0;

      // Maximize the Image AOI.
      if (IsWritable(offsetX)) {
        //use maximum possible offset / 2 (and -1 if odd nr of pixels)
        tmp_offset = offsetX->GetMax()/2;
        tmp_offset = tmp_offset-tmp_offset%2;
        offsetX->SetValue(tmp_offset);
      }
      if (IsWritable(offsetY)) {
        tmp_offset = offsetY->GetMax()/2;
        tmp_offset = tmp_offset-tmp_offset%2;
        offsetY->SetValue(tmp_offset);
      }

      // Set the pixel data format.
      //CEnumerationPtr(control.GetNode("PixelFormat"))->FromString("Mono8");

      //set a good exposure time
      if (this->config["exposureTime"])
       CIntegerPtr(control.GetNode("ExposureTimeRaw"))->SetValue(this->config["exposureTime"]);

      //tcp packet size
      const CIntegerPtr packetSize = control.GetNode("GevSCPSPacketSize");
      packetSize->SetValue(1500);

      //-- Configure gain

      //Set raw gain value
      if (this->config["gainRaw"])
        CIntegerPtr(control.GetNode("GainRaw"))->SetValue(this->config["gainRaw"]);

      //-- Configure white balance

      if (this->config["whiteBalance"]) {
        // Set the red intensity
        CEnumerationPtr(control.GetNode("BalanceRatioSelector"))->FromString("Red");
        CFloatPtr(control.GetNode("BalanceRatioAbs"))->SetValue(this->config["whiteBalance"]["red"]);

        // Set the green intensity
        CEnumerationPtr(control.GetNode("BalanceRatioSelector"))->FromString("Green");
        CFloatPtr(control.GetNode("BalanceRatioAbs"))->SetValue(this->config["whiteBalance"]["green"]);

        // Set the blue intensity
        CEnumerationPtr(control.GetNode("BalanceRatioSelector"))->FromString("Blue");
        CFloatPtr(control.GetNode("BalanceRatioAbs"))->SetValue(this->config["whiteBalance"]["blue"]);
      }

      //-- Configure black level
      if (this->config["blackLevel"])
        CIntegerPtr(control.GetNode("BlackLevelRaw"))->SetValue(this->config["blackLevel"]);

      //-- Configure digital shift
      if (this->config["digitalShift"])
        CIntegerPtr(control.GetNode("DigitalShift"))->SetValue(this->config["digitalShift"]);

      //-- Configure gamma correction
      if (this->config["gamma"]) {
        CBooleanPtr(control.GetNode("GammaEnable"))->SetValue(true);
        CEnumerationPtr(control.GetNode("GammaSelector"))->FromString("User");
        CFloatPtr(control.GetNode("Gamma"))->SetValue(this->config["gamma"]);
      } else {
        CBooleanPtr(control.GetNode("GammaEnable"))->SetValue(false);
      }

      //-- Configure lightsource presets
      // If active sets presets for white balance, color adjustment and color transformation
      // Presets:
      //   Off
      //   Daylight 5000 K
      //   Daylight 6500 K
      //   Tungsten
      //   Custom

      if (this->config["useLightPreset"]) {
        CEnumerationPtr(control.GetNode("LightSourceSelector"))->FromString(this->config["useLightPreset"]);
      } else {
        CEnumerationPtr(control.GetNode("LightSourceSelector"))->FromString("Off");
      }

      if (this->config["reverseX"]) {
        CBooleanPtr(control.GetNode("ReverseX"))->SetValue(["reverseX"]);
      }

      if (this->config["reverseY"]) {
        CBooleanPtr(control.GetNode("ReverseY"))->SetValue(["reverseY"]);
      }

    }
    catch (GenICam::GenericException& e)
    {
      throw RUNTIME_EXCEPTION( "Could not apply configuration. GenICam::GenericException caught in OnOpened method msg=%hs", e.what());
    }
  }

  json config;
};

#endif /* INCLUDED_CAMERACONFIGURATION_H_00104928 */
