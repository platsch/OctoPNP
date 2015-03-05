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
    along with OctoPNP.  If not, see <http://www.gnu.org/licenses/>.

    Main author: Florens Wasserfall <wasserfall@informatik.uni-hamburg.de>
*/

/*
	This is a simple program to fetch images from basler cameras based on the pylon API.
	It will detect up to 5 attached cameras and save an uncompressed 1000x1000px image to the disk every 500ms to "cameraname.tiff".
*/


// Include files to use the PYLON API.
#include <pylon/PylonIncludes.h>
#ifdef PYLON_WIN_BUILD
#    include <pylon/PylonGUI.h>
#endif

#include "./inc/PixelFormatAndAoiConfiguration.h"

#include <iostream>
#ifdef WIN32
#include <windows.h>
#else
#include <unistd.h>
#endif																														

// Namespace for using pylon objects.
using namespace Pylon;

// Namespace for using cout.
using namespace std;

// Limits the amount of cameras used for grabbing.
// It is important to manage the available bandwidth when grabbing with multiple cameras.
// This applies, for instance, if two GigE cameras are connected to the same network adapter via a switch.
// To manage the bandwidth, the GevSCPD interpacket delay parameter and the GevSCFTD transmission delay
// parameter can be set for each GigE camera device.
// The "Controlling Packet Transmission Timing with the Interpacket and Frame Transmission Delays on Basler GigE Vision Cameras"
// Application Notes (AW000649xx000)
// provide more information about this topic.
// The bandwidth used by a FireWire camera device can be limited by adjusting the packet size.
static const size_t c_maxCamerasToUse = 5;

int main(int argc, char* argv[])
{
	int exitCode = 0;
    // Automagically call PylonInitialize and PylonTerminate to ensure the pylon runtime system.
    // is initialized during the lifetime of this object
    Pylon::PylonAutoInitTerm autoInitTerm;

	//use basedir given by parameter
	String_t basedir = "";
	if(argc > 1) {
		basedir = argv[1];
	}

    try
    {
        // Get the transport layer factory.
        CTlFactory& tlFactory = CTlFactory::GetInstance();

        // Get all attached devices and exit application if no device is found.
        DeviceInfoList_t devices;
        if ( tlFactory.EnumerateDevices(devices) == 0 )
        {
            throw RUNTIME_EXCEPTION( "No camera present.");
        }

        // Create an array of instant cameras for the found devices and avoid exceeding a maximum number of devices.
        CInstantCameraArray cameras( min( devices.size(), c_maxCamerasToUse));

		// This smart pointer will receive the grab result data.
        CGrabResultPtr ptrGrabResult;

        // Create and attach all Pylon Devices.
        for ( size_t i = 0; i < cameras.GetSize(); ++i)
        {
            cameras[ i ].Attach( tlFactory.CreateDevice( devices[ i ]));

			// Register an additional configuration handler to set the image format and adjust the AOI.
        	// By setting the registration mode to RegistrationMode_Append, the configuration handler is added instead of replacing
        	// the already registered configuration handler.
        	cameras[i].RegisterConfiguration( new CPixelFormatAndAoiConfiguration, RegistrationMode_Append, Cleanup_Delete);

            // Print the model name of the camera.
            cout << "Using device " << cameras[ i ].GetDeviceInfo().GetModelName() << " device name: " << cameras[i].GetDeviceInfo().GetUserDefinedName() << endl;
        }

		//grab images and save to disk
		//while(true) {
			for ( size_t i = 0; i < cameras.GetSize(); ++i) {
				if ( cameras[i].GrabOne( 5000, ptrGrabResult))
				{
					// use user defined camera name as filename
					String_t filename = basedir + "/" + cameras[i].GetDeviceInfo().GetUserDefinedName() + ".tiff";

				    // The pylon grab result smart pointer classes provide a cast operator to the IImage
				    // interface. This makes it possible to pass a grab result directly to the
				    // function that saves an image to disk.
					cout << "Save image to " << filename << endl;
				    CImagePersistence::Save( ImageFileFormat_Tiff, filename, ptrGrabResult);
				}
			}
			/*#ifdef WIN32
			Sleep(500);
			#else
			usleep(500 * 1000);
			#endif // win32
        }*/

      
    }
    catch (GenICam::GenericException &e)
    {
        // Error handling
        cerr << "An exception occurred." << endl
        << e.GetDescription() << endl;
        exitCode = 1;
    }

    return exitCode;
}
