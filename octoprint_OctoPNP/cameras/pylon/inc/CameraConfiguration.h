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

using json = nlohmann::json;

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

      width->SetValue(this->config["image_size"]);
      height->SetValue(this->config["image_size"]);

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
      const CIntegerPtr exposureTimeRaw = control.GetNode("ExposureTimeRaw");
      exposureTimeRaw->SetValue(this->config["exposure_time"]);

      //tcp packet size
      const CIntegerPtr packetSize = control.GetNode("GevSCPSPacketSize");
      packetSize->SetValue(1500);

      //-- Configure gain

      //Set raw gain value
      const CIntegerPtr gainRaw = control.GetNode("GainRaw");
      gainRaw->SetValue(this->config["gainRaw"]);


      //-- Configure white balance

      // Set the red intensity
      CEnumerationPtr(control.GetNode("BalanceRatioSelector"))->FromString("Red");
      CFloatPtr(control.GetNode("BalanceRatioAbs"))->SetValue(this->config["red"]);

      // Set the green intensity
      CEnumerationPtr(control.GetNode("BalanceRatioSelector"))->FromString("Green");
      CFloatPtr(control.GetNode("BalanceRatioAbs"))->SetValue(this->config["green"]);

      // Set the blue intensity
      CEnumerationPtr(control.GetNode("BalanceRatioSelector"))->FromString("Blue");
      CFloatPtr(control.GetNode("BalanceRatioAbs"))->SetValue(this->config["blue"]);

    }
    catch (GenICam::GenericException& e)
    {
      throw RUNTIME_EXCEPTION( "Could not apply configuration. GenICam::GenericException caught in OnOpened method msg=%hs", e.what());
    }
  }

  json config;
};

#endif /* INCLUDED_CAMERACONFIGURATION_H_00104928 */
