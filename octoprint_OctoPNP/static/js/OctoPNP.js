$(function() {
    function OctoPNPViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];

        self.tray = {}
        self.camera = {}
        self.vacnozzle = {}

        self.stateString = ko.observable("No file loaded");
        self.currentOperation = ko.observable("");
        self.debugvar = ko.observable("");
        //white placeholder images
        document.getElementById('headCameraImage').setAttribute( 'src', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3wMRCQAfAmB4CgAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAAAMSURBVAjXY/j//z8ABf4C/tzMWecAAAAASUVORK5CYII=');
        document.getElementById('bedCameraImage').setAttribute( 'src', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3wMRCQAfAmB4CgAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAAAMSURBVAjXY/j//z8ABf4C/tzMWecAAAAASUVORK5CYII=');

        self.trayCanvas = document.getElementById('trayCanvas');

        //internal variables
        self.cols = 0;
        self.rows = 0;
        self.parts = {};

        // This will get called before the HelloWorldViewModel gets bound to the DOM, but after its depedencies have
        // already been initialized. It is especially guaranteed that this method gets called _after_ the settings
        // have been retrieved from the OctoPrint backend and thus the SettingsViewModel been properly populated.
        self.onBeforeBinding = function() {
            self.tray = self.settings.settings.plugins.OctoPNP.tray;
            self.camera = self.settings.settings.plugins.OctoPNP.camera;
            self.vacnozzle = self.settings.settings.plugins.OctoPNP.vacnozzle;
        }


        self.getBoxSize = function() {
            var boxSize = 0;
            if (self.trayCanvas && self.trayCanvas.getContext) {
                var ctx = self.trayCanvas.getContext("2d");
                if (ctx) {
                    var size_x = ctx.canvas.width;
                    var size_y = ctx.canvas.height;
                    boxSize = Math.min((size_x-4)/self.cols, (size_y-4)/self.rows);
                }
            }
            return boxSize;
        }


		self.drawTray = function(rows, cols) {
			self.cols = cols;
			self.rows = rows;
			if (self.trayCanvas && self.trayCanvas.getContext) {
                var ctx = self.trayCanvas.getContext("2d");
                if (ctx) {
                    var size_x = ctx.canvas.width;
                    var size_y = ctx.canvas.height;
                    var boxSize = self.getBoxSize();

                    //initialize white tray
                    ctx.strokeStyle = "black";
                    ctx.fillStyle = "white";
                    ctx.lineWidth = 1;
                    ctx.fillRect(0,0,size_x,size_y);
                    ctx.strokeRect (0,0,size_x,size_y);

					for(var x=0; x<cols; x++) {
                        for(var y=0; y<rows; y++) {
                            self.drawTrayBox(x, y, boxSize);
                        }
                    }
                }
            }
		}

        //draw a single tray box
        self.drawTrayBox = function(col, row, size) {
            if (self.trayCanvas && self.trayCanvas.getContext) {
	            var ctx = self.trayCanvas.getContext("2d");
	            if (ctx) {
	                ctx.lineWidth = 4;
	                ctx.strokeStyle = "green";
	                ctx.fillStyle = "white";
	                ctx.strokeRect (col*size+ctx.lineWidth/2,row*size+ctx.lineWidth/2,size-ctx.lineWidth/2,size-ctx.lineWidth/2);
	                ctx.fillRect (col*size+ctx.lineWidth,row*size+ctx.lineWidth,size-ctx.lineWidth,size-ctx.lineWidth);
	            }
	        }
        }

        //draw a part into a tray box
        self.drawPart = function(part) {
            var row = parseInt(((part.partPosition-1) / self.cols)) + 1;
			var col = (part.partPosition-1) % self.cols+1;

			//clear old box
			var boxSize = self.getBoxSize();
			self.drawTrayBox(col-1, row-1, boxSize);

			if (self.trayCanvas && self.trayCanvas.getContext) {
	            var ctx = self.trayCanvas.getContext("2d");
	            var scale = boxSize/self.tray.boxsize();
	            if (ctx) {
	                var col_offset = col*boxSize-boxSize+4;
	                var row_offset = row*boxSize-boxSize+4;

	                //print part names
					ctx.font = "10px Verdana";
					ctx.fillStyle = "#000000";
					ctx.textBaseline = "top";
					ctx.fillText(part.name, col_offset, row_offset);

					//draw part shapes
					if( part.hasOwnProperty("shape") ) {
						var points = part.shape;

						ctx.beginPath();
						ctx.strokeStyle = "#000000";
						ctx.fillStyle = "#000000";
						ctx.moveTo(points[0][0]*scale+col_offset+boxSize/2, points[0][1]*scale+row_offset+boxSize/2);
						for(var i=0; i < points.length; i++) {
							ctx.lineTo(points[i][0]*scale+col_offset+boxSize/2, points[i][1]*scale+row_offset+boxSize/2);
						}
						//close loop
						ctx.lineTo(points[0][0]*scale+col_offset+boxSize/2, points[0][1]*scale+row_offset+boxSize/2);
						ctx.lineTo(points[1][0]*scale+col_offset+boxSize/2, points[1][1]*scale+row_offset+boxSize/2);
						ctx.stroke();
						ctx.fill();
					}

					//draw part pads
					if( part.hasOwnProperty("pads") ) {
						var pads = part.pads;

						ctx.beginPath();
						ctx.fillStyle = "#999999";
						console.log(pads);
						for(var i=0; i < pads.length; i++) {
							ctx.fillRect(pads[i][0]*scale+col_offset+boxSize/2, pads[i][1]*scale+row_offset+boxSize/2, (pads[i][2]-pads[i][0])*scale, (pads[i][3]-pads[i][1])*scale);
						}
					}
	            }
	        }
        }

         self.onDataUpdaterPluginMessage = function(plugin, data) {
            if(plugin == "OctoPNP") {
                if(data.event == "FILE") {
                    if(data.data.hasOwnProperty("partCount")) {
                        self.stateString("Loaded file with " + data.data.partCount + " SMD parts");
                        //initialize the tray
                        self.drawTray(data.data.tray.rows, data.data.tray.cols);

						//extract part information
                        if( data.data.hasOwnProperty("parts") ) {
							var parts = data.data.parts;
							for(var i=0; i < parts.length; i++) {
								self.drawPart(parts[i]);
							}
						}
                    }else{
                        self.stateString("No SMD part in this file!");
                    }
                }
                else if(data.event == "OPERATION") {
                    self.currentOperation(data.data.type + " part nr " + data.data.part);
                }
                else if(data.event == "ERROR") {
                    self.stateString("ERROR: \"" + data.data.type + "\"");
                    if(data.data.hasOwnProperty("part")) {
                        self.stateString(self.StateString + "appeared while processing part nr " + data.data.part);
                    }
                }
                else if(data.event == "HEADIMAGE") {
                    document.getElementById('headCameraImage').setAttribute( 'src', data.data.src );
                }
                else if(data.event == "BEDIMAGE") {
                    document.getElementById('bedCameraImage').setAttribute( 'src', data.data.src );
                }
                //self.debugvar("Plugin = OctoPNP");
            }
        };
    }

    // This is how our plugin registers itself with the application, by adding some configuration information to
    // the global variable ADDITIONAL_VIEWMODELS
    ADDITIONAL_VIEWMODELS.push([
        // This is the constructor to call for instantiating the plugin
        OctoPNPViewModel,

        // This is a list of dependencies to inject into the plugin, the order which you request here is the order
        // in which the dependencies will be injected into your view model upon instantiation via the parameters
        // argument
        ["settingsViewModel"],

        // Finally, this is the list of all elements we want this view model to be bound to.
        [document.getElementById("tab_plugin_OctoPNP"), document.getElementById("settings_plugin_OctoPNP")]
    ]);
});
