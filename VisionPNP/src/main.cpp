#include "../include/image.h"
#include "../include/color.h"
#include <iostream>
using namespace std;
using namespace cv;

int main(int argc, const char* argv[])
{
  // TODO: Function calls have changed and need to be updated.
  //-- BEGIN Gripper part - uncomment to run:
  // vector <vector<int>> thresh;
  // thresh = Color::getHSVColorRange("../resources/gripper.png");

  // float orientation = Image::matchTemplate("../resources/tiny-on-gripper.png", "../resources/template-output.png", thresh);
  // cout << "Orientation:" << endl;
  // cout << orientation << endl;
  // //-- END Gripper part

  // //-- BEGIN Tray part - uncomment to run:
  // vector<int> center = Image::findShape("../resources/tray_resistor.png");
  // cout << "Position:" << endl;
  // cout << center[0] << " " << center[1] << endl;
  // //-- END Tray part
}
