# -*- coding: utf-8 -*-

""" This file is part of OctoPNP
    
    This is a test script to execute the imageprocessing-steps independent from the main software
    and particularly without a running printer.
   
    Main author: Florens Wasserfall <wasserfall@kalanka.de>
"""

import ImageProcessing
import time

im = ImageProcessing.ImageProcessing(15.0, 150, 120)


start_time = time.time()

im._interactive = True
#im.locatePartInBox("../utils/testimages/head_atmega_SO8.png")
#im.locatePartInBox("../utils/testimages/head_resistor_1206.png")
im.getPartOrientation("../utils/testimages/bed_atmega_SO8.png")
#im.getPartOrientation("../utils/testimages/bed_resistor_1206.png")
#im.getPartPosition("../utils/testimages/bed_atmega_SO8.png", 55.65)
#im.getPartPosition("../utils/testimages/bed_resistor_1206.png", 55.65)

end_time = time.time();
print("--- %s seconds ---" % (time.time() - start_time))
