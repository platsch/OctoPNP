$(function() {
    function OctoPNPSettingsViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];
        self.control = parameters[1];
        self.connection = parameters[2];

        self._headCanvas = document.getElementById('headCanvas');

        self.objectPositionX = ko.observable(100.0);
        self.objectPositionY = ko.observable(100.0);

        self.offsetCorrectionX = ko.observable(0.0);
        self.offsetCorrectionY = ko.observable(0.0);
        self.jogDistance = ko.observable(1.0);

        self.selectedHeadExtruder = ko.observable(0);
        self.selectedBedExtruder = ko.observable(1);

        self.isConnected = ko.computed(function() {
            return self.connection.isOperational() || self.connection.isReady() || self.connection.isPaused();
        });

        self.statusHeadCameraOffset = ko.observable(false);
        self.statusTrayPosition = ko.observable(false);
        self.statusBedCameraOffset = ko.observable(false);
        // delete if pnp offset in eeprom
        self.statusPnpNozzleOffset =  ko.observable(false);

        self.keycontrolPossible = ko.observable(false);
        self.keycontrolActive = ko.observable(false);
        self.showKeycontrols = ko.observable(true);
        self.keycontrolHelpActive = ko.observable(false);

        // helpers for eeprom access
        self.firmwareRegEx = /FIRMWARE_NAME:([^\s]+)/i;
        self.repetierRegEx = /Repetier_([^\s]*)/i;
        self.eepromDataRegEx = /EPR:(\d+) (\d+) ([^\s]+) (.+)/;
        self.isRepetierFirmware = ko.observable(false);
        self.eepromData = ko.observableArray([]);


        // This will get called before the ViewModel gets bound to the DOM, but after its depedencies have
        // already been initialized. It is especially guaranteed that this method gets called _after_ the settings
        // have been retrieved from the OctoPrint backend and thus the SettingsViewModel been properly populated.
        self.onBeforeBinding = function() {
            self.settings = self.settings.settings;
        };
        
        // Home X Y
        self.homeXY = function() {

            self.control.sendCustomCommand({command: "G1 X100 Y150 F3000"});
            self.control.sendCustomCommand({command: "T0"});
            self.control.sendCustomCommand({command: "G28 X Y"});
        };
        
        // Calibrate offset between primary extruder and head-camera
        self.headCameraOffset = function() {
            //deactivate other processes
            self.statusHeadCameraOffset(true);
            self.statusTrayPosition(false);
            self.statusBedCameraOffset(false);
            // delete if pnp offset in eeprom
            self.statusPnpNozzleOffset(false);
            
            // Load eeprom for extruder calibation
            self.loadEeprom();

            // Switch to primary extruder
            self.control.sendCustomCommand({command: "G1 X100 Y150 F3000"});
            self.control.sendCustomCommand({command: "T0"});

            //move camera to object
            var x = self.objectPositionX() - parseFloat(self.settings.plugins.OctoPNP.camera.head.x());
            var y = self.objectPositionY() - parseFloat(self.settings.plugins.OctoPNP.camera.head.y());
            self.control.sendCustomCommand({command: "G1 X" + x + " Y" + y + " Z" + self.settings.plugins.OctoPNP.camera.head.z() + " F3000"});

            //reset offset correction values
            self.offsetCorrectionX(0.0);
            self.offsetCorrectionY(0.0);

            //activate Keycontrol
            self.keycontrolPossible(true);

            //trigger immage fetching
            setTimeout(function() {self._getImage('HEAD');}, 8000);
        };

        self.saveHeadCameraOffset = function() {
            //save values...
            self.settings.plugins.OctoPNP.camera.head.x(parseFloat(self.settings.plugins.OctoPNP.camera.head.x())-self.offsetCorrectionX());
            self.settings.plugins.OctoPNP.camera.head.y(parseFloat(self.settings.plugins.OctoPNP.camera.head.y())-self.offsetCorrectionY());

            //deactivate Keycontrol
            self.keycontrolPossible(false);
            self.statusHeadCameraOffset(false);
        };


        self.saveExtruderOffset = function(ex) {
            // Steps to save values:
            // get current Extuder EEPROM starting with E1
            ex = parseInt(ex)+1;
            ex = ex.toString();

            // get current offset for extruder x from eeprom
            var oldOffsetX = parseFloat(self._getEepromValue("Extr." + ex + " X-offset"));
            var oldOffsetY = parseFloat(self._getEepromValue("Extr." + ex + " Y-offset"));
            // get steps per mm for x and y axis
            var stepsPerMMX = parseFloat(self._getEepromValue("X-axis steps per mm"));
            var stepsPerMMY = parseFloat(self._getEepromValue("Y-axis steps per mm"));
            // compute offset steps from offsetCorrection values
            var offsetX = oldOffsetX + self.offsetCorrectionX() * stepsPerMMX;
            var offsetY = oldOffsetY + self.offsetCorrectionY() * stepsPerMMY;
            // save to eeprom
            self._setEepromValue("Extr." + ex + " X-offset", offsetX);
            self._setEepromValue("Extr." + ex + " Y-offset", offsetY);
            //console.log(offsetX);
            //console.log(offsetY);
            self.saveEeprom();
            
            //reset offset correction values
            self.offsetCorrectionX(0.0);
            self.offsetCorrectionY(0.0);

            // deactivate Keycontrol
            self.keycontrolPossible(false);
        };

        // Move Ex to bed camera.
        self.bedCameraPosition = function() {
            //deactivate other processes
            self.statusHeadCameraOffset(false);
            self.statusTrayPosition(false);
            self.statusBedCameraOffset(true);
            // delete if pnp offset in eeprom
            self.statusPnpNozzleOffset(false);

            // Switch to VacNozzle extruder
            self.control.sendCustomCommand({command: "G1 X100 Y150 F3000"});
            self.control.sendCustomCommand({command: "T" + self.selectedBedExtruder().toString()});

            //move camera to object
            var x = parseFloat(self.settings.plugins.OctoPNP.camera.bed.x());
            var y = parseFloat(self.settings.plugins.OctoPNP.camera.bed.y());
            self.control.sendCustomCommand({command: "G1 X" + x + " Y" + y + " Z" + self.settings.plugins.OctoPNP.camera.bed.z() + " F3000"});

            //reset offset correction values
            self.offsetCorrectionX(0.0);
            self.offsetCorrectionY(0.0);

            //activate Keycontrol
            self.keycontrolPossible(true);

            //trigger immage fetching
            setTimeout(function() {self._getImage('BED');}, 8000);
        };
        
        self.saveExtruderHeadCameraOffset = function() {
            // save offset
            self.saveExtruderOffset(self.selectedHeadExtruder());
            
            // deactivate Button
            self.statusHeadCameraOffset(false);
        };
        
        
        self.saveExtruderBedCameraOffset = function() {
            // invert X and Y axis
            self.offsetCorrectionX(self.offsetCorrectionX()*-1);
            self.offsetCorrectionY(self.offsetCorrectionY()*-1);
            
            // save offset
            self.saveExtruderOffset(self.selectedBedExtruder());
            
            // deactivate Button
            self.statusBedCameraOffset(false);
        };

        
        self.saveBedCameraPosition = function() {
            //save values
            self.settings.plugins.OctoPNP.camera.bed.x(parseFloat(self.settings.plugins.OctoPNP.camera.bed.x())+self.offsetCorrectionX());
            self.settings.plugins.OctoPNP.camera.bed.y(parseFloat(self.settings.plugins.OctoPNP.camera.bed.y())+self.offsetCorrectionY());

            //deactivate Keycontrol
            
            self.keycontrolPossible(false);
            self.statusBedCameraOffset(false);
        };
        
        
        // delete if pnp offset in eeprom
        // Move Vacuum bed camera to Nozzle.
        self.pnpNozzleOffset = function() {
            //deactivate other processes
            self.statusHeadCameraOffset(false);
            self.statusTrayPosition(false);
            self.statusBedCameraOffset(false);
            // delete if pnp offset in eeprom
            self.statusPnpNozzleOffset(true);

            // Move before toolchange
            //reset axis
            self.control.sendCustomCommand({command: "G1 X100 Y150 F3000"});
            // Switch to VacNozzle extruder
            self.control.sendCustomCommand({command: "T" + self.settings.plugins.OctoPNP.vacnozzle.extruder_nr().toString()});
            
            //move camera to object
            var x = parseFloat(self.settings.plugins.OctoPNP.camera.bed.x()) - parseFloat(self.settings.plugins.OctoPNP.vacnozzle.x());
            var y = parseFloat(self.settings.plugins.OctoPNP.camera.bed.y()) - parseFloat(self.settings.plugins.OctoPNP.vacnozzle.y());
            self.control.sendCustomCommand({command: "G1 X" + x + " Y" + y + " Z" + self.settings.plugins.OctoPNP.camera.bed.z() + " F3000"});
            
            //reset offset correction values
            self.offsetCorrectionX(0.0);
            self.offsetCorrectionY(0.0);

            //activate Keycontrol
            self.keycontrolPossible(true);

            //trigger immage fetching
            setTimeout(function() {self._getImage('BED');}, 8000);
        };
        
        // delete if pnp offset in eeprom
        self.savePnpNozzleOffset = function() {
            //save values
            self.settings.plugins.OctoPNP.vacnozzle.x(parseFloat(self.settings.plugins.OctoPNP.vacnozzle.x())-self.offsetCorrectionX());
            self.settings.plugins.OctoPNP.vacnozzle.y(parseFloat(self.settings.plugins.OctoPNP.vacnozzle.y())-self.offsetCorrectionY());

            //deactivate Keycontrol
            self.keycontrolPossible(false);
            self.statusPnpNozzleOffset(false);
        };
        
        // calibrate tray position relative to primary extruder
        self.trayPosition = function(corner) {
            //deactivate other processes
            self.statusHeadCameraOffset(false);
            self.statusTrayPosition(true);
            self.statusBedCameraOffset(false);
            // delete if pnp offset in eeprom
            self.statusPnpNozzleOffset(false);

            // Switch to primary extruder
            self.control.sendCustomCommand({command: "G1 X100 Y150 F3000"});
            self.control.sendCustomCommand({command: "T0"});

            //computer corner position
            var cornerOffsetX = 0.0;
            var cornerOffsetY = 0.0;
            switch (corner) {
                case "TL": 
                    var rows = parseFloat(self.settings.plugins.OctoPNP.tray.rows());
                    cornerOffsetY = rows*parseFloat(self.settings.plugins.OctoPNP.tray.boxsize()) + (rows+1)*parseFloat(self.settings.plugins.OctoPNP.tray.rimsize());
                    self.statusTrayPosition(false);
                    break;
                case "TR": 
                    var rows = parseFloat(self.settings.plugins.OctoPNP.tray.rows());
                    var cols = parseFloat(self.settings.plugins.OctoPNP.tray.columns());
                    cornerOffsetY = rows*parseFloat(self.settings.plugins.OctoPNP.tray.boxsize()) + (rows+1)*parseFloat(self.settings.plugins.OctoPNP.tray.rimsize());
                    cornerOffsetX = cols*parseFloat(self.settings.plugins.OctoPNP.tray.boxsize()) + (cols+1)*parseFloat(self.settings.plugins.OctoPNP.tray.rimsize());
                    self.statusTrayPosition(false);
                    break;
                case "BR": 
                    var cols = parseFloat(self.settings.plugins.OctoPNP.tray.columns());
                    cornerOffsetX = cols*parseFloat(self.settings.plugins.OctoPNP.tray.boxsize()) + (cols+1)*parseFloat(self.settings.plugins.OctoPNP.tray.rimsize());
                    self.statusTrayPosition(false);
                    break;
                default:
                    // BL is default case, the tray position is allways computed for this point. Saving the calibration
                    // is only possible for this case.
                    break;
            }

            //move camera to tray
            var x = parseFloat(self.settings.plugins.OctoPNP.tray.x()) + cornerOffsetX - parseFloat(self.settings.plugins.OctoPNP.camera.head.x());
            var y = parseFloat(self.settings.plugins.OctoPNP.tray.y()) + cornerOffsetY - parseFloat(self.settings.plugins.OctoPNP.camera.head.y());
            var z = parseFloat(self.settings.plugins.OctoPNP.tray.z()) + parseFloat(self.settings.plugins.OctoPNP.camera.head.z());
            console.log(self.settings.plugins.OctoPNP.tray.z());
            console.log(self.settings.plugins.OctoPNP.camera.head.z());
            console.log(z);
            self.control.sendCustomCommand({command: "G1 X" + x + " Y" + y + " Z" + z + " F3000"});

            //reset offset correction values
            self.offsetCorrectionX(0.0);
            self.offsetCorrectionY(0.0);

            //activate Keycontrol
            self.keycontrolPossible(true);

            //trigger immage fetching
            setTimeout(function() {self._getImage('HEAD');}, 8000);
        };

        self.saveTrayPosition = function() {
            //save values
            self.settings.plugins.OctoPNP.tray.x(parseFloat(self.settings.plugins.OctoPNP.tray.x())+self.offsetCorrectionX());
            self.settings.plugins.OctoPNP.tray.y(parseFloat(self.settings.plugins.OctoPNP.tray.y())+self.offsetCorrectionY());

            //deactivate Keycontrol
            self.keycontrolPossible(false);
            self.statusTrayPosition(false);
        };


        self._getImage = function(imagetype, callback) {
            $.ajax({
                url: PLUGIN_BASEURL + "OctoPNP/camera_image?imagetype=" + imagetype,
                type: "GET",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                //data: JSON.stringify(data),
                success: function(response) {
                    if(response.hasOwnProperty("src")) {
                        self._drawImage(response.src);
                    }
                    if(response.hasOwnProperty("error")) {
                        alert(response.error);
                    }
                    if (callback) callback();
                }
            });
        };

        self._drawImage = function(img) {
            var ctx=self._headCanvas.getContext("2d");  
            var localimg = new Image();
            localimg.src = img;
            localimg.onload = function () {
                var w = localimg.width;
                var h = localimg.height;
                var scale = Math.min(ctx.canvas.clientWidth/w, ctx.canvas.clientHeight/h,1);
                ctx.drawImage(localimg, 0, 0, w*scale, h*scale);

                // crosshairs
                ctx.beginPath();
                ctx.strokeStyle = "#000000";
                ctx.lineWidth = 1;
                ctx.fillStyle = "#000000";
                ctx.fillRect(0, ((h*scale)/2)-0.5, w*scale, 1);
                ctx.fillRect(((w*scale)/2)-0.5, 0, 1, h*scale);
            };
        };

        self.onFocus = function (data, event) {
            if (!self.keycontrolPossible) return;
            self.keycontrolActive(true);
        };

        self.onMouseOver = function (data, event) {
            if (!self.keycontrolPossible) return;
            $("#webcam_container").focus();
            self.keycontrolActive(true);
        };

        self.onMouseOut = function (data, event) {
            $("#webcam_container").blur();
            self.keycontrolActive(false);
        };

        self.toggleKeycontrolHelp = function () {
            self.keycontrolHelpActive(!self.keycontrolHelpActive());
        };

        self.onKeyDown = function (data, event) {
            var refreshImage = false;

            switch (event.which) {
                case 37: // left arrow key
                    // X-
                    self.control.sendJogCommand("x", -1, self.jogDistance());
                    self.offsetCorrectionX(parseFloat((self.offsetCorrectionX()-self.jogDistance()).toFixed(2)));
                    refreshImage = true;
                    break;
                case 38: // up arrow key
                    // Y+
                    self.control.sendJogCommand("y", 1, self.jogDistance());
                    self.offsetCorrectionY(parseFloat((self.offsetCorrectionY()+self.jogDistance()).toFixed(2)));
                    refreshImage = true;
                    break;
                case 39: // right arrow key
                    // X+
                    self.control.sendJogCommand("x", 1, self.jogDistance());
                    self.offsetCorrectionX(parseFloat((self.offsetCorrectionX()+self.jogDistance()).toFixed(2)));
                    refreshImage = true;
                    break;
                case 40: // down arrow key
                    // Y-
                    self.control.sendJogCommand("y", -1, self.jogDistance());
                    self.offsetCorrectionY(parseFloat((self.offsetCorrectionY()-self.jogDistance()).toFixed(2)));
                    refreshImage = true;
                    break;
                case 49: // number 1
                case 97: // numpad 1
                    // Distance 0.1
                    self.jogDistance(0.1);
                    break;
                case 50: // number 2
                case 98: // numpad 2
                    // Distance 1
                    self.jogDistance(1.0);
                    break;
                case 51: // number 3
                case 99: // numpad 3
                    // Distance 10
                    self.jogDistance(10.0);
                    break;
                case 52: // number 4
                case 100: // numpad 4
                    // Distance 100
                    self.jogDistance(100.0);
                    break;
                case 33: // page up key
                case 87: // w key
                    // z lift up
                    break;
                case 34: // page down key
                case 83: // s key
                    // z lift down
                    break;
                case 36: // home key
                    // xy home
                    break;
                case 35: // end key
                    // z home
                    break;
                default:
                    event.preventDefault();
                    return false;
            }
            if(refreshImage) {
                if(self.statusBedCameraOffset() || self.statusPnpNozzleOffset()) {
                    setTimeout(function() {self._getImage('BED');}, 300);
                }else{
                    setTimeout(function() {self._getImage('HEAD');}, 300);
                }
            }
        };


        // The following functions provide "infrastructure" to access and modify eeprom values
        self.onStartup = function() {
            $('#settings_plugin_OctoPNP_link a').on('show', function(e) {
                if (self.isConnected() && !self.isRepetierFirmware())
                    self._requestFirmwareInfo();
            });
        }

        self.fromHistoryData = function(data) {
            _.each(data.logs, function(line) {
                var match = self.firmwareRegEx.exec(line);
                if (match != null) {
                    if (self.repetierRegEx.exec(match[0]))
                        self.isRepetierFirmware(true);
                }
            });
        };

        self.fromCurrentData = function(data) {
            if (!self.isRepetierFirmware()) {
                _.each(data.logs, function (line) {
                    var match = self.firmwareRegEx.exec(line);
                    if (match) {
                        if (self.repetierRegEx.exec(match[0]))
                            self.isRepetierFirmware(true);
                    }
                });
            }
            else
            {
                _.each(data.logs, function (line) {
                    var match = self.eepromDataRegEx.exec(line);
                    if (match) {
                        self.eepromData.push({
                            dataType: match[1],
                            position: match[2],
                            origValue: match[3],
                            value: match[3],
                            description: match[4]
                        });
                    }
                });
            }
        };

        self.onEventConnected = function() {
            self._requestFirmwareInfo();
        }

        self.onEventDisconnected = function() {
            self.isRepetierFirmware(false);
        };

        self.loadEeprom = function() {
            self.eepromData([]);
            self._requestEepromData();
        };

        self.saveEeprom = function()  {
            var eepromData = self.eepromData();
            _.each(eepromData, function(data) {
                if (data.origValue != data.value) {
                    self._requestSaveDataToEeprom(data.dataType, data.position, data.value);
                    data.origValue = data.value;
                }
            });
        };

        self._getEepromValue = function(description) {
            var eepromData = self.eepromData();
            var result = false;
            _.each(eepromData, function(data) {
                if ((new RegExp(description)).test(data.description)) {
                    result = data.value;
                }
            });
            return result;
        }

        self._setEepromValue = function(description, value) {
            var eepromData = self.eepromData();
            var result = false;
            _.each(eepromData, function(data) {
                if ((new RegExp(description)).test(data.description)) {
                    data.value = value;
                }
            });
        }

        self._requestFirmwareInfo = function() {
            self.control.sendCustomCommand({ command: "M115" });
        };

        self._requestEepromData = function() {
            self.control.sendCustomCommand({ command: "M205" });
        }
        self._requestSaveDataToEeprom = function(data_type, position, value) {
            var cmd = "M206 T" + data_type + " P" + position;
            if (data_type == 3) {
                cmd += " X" + value;
                self.control.sendCustomCommand({ command: cmd });
            }
            else {
                cmd += " S" + value;
                self.control.sendCustomCommand({ command: cmd });
            }
        }
    }


    // This is how our plugin registers itself with the application, by adding some configuration information to
    // the global variable ADDITIONAL_VIEWMODELS
    ADDITIONAL_VIEWMODELS.push([
        // This is the constructor to call for instantiating the plugin
        OctoPNPSettingsViewModel,

        // This is a list of dependencies to inject into the plugin, the order which you request here is the order
        // in which the dependencies will be injected into your view model upon instantiation via the parameters
        // argument
        ["settingsViewModel", "controlViewModel", "connectionViewModel"],

        // Finally, this is the list of all elements we want this view model to be bound to.
        "#settings_plugin_OctoPNP"
    ]);
});
