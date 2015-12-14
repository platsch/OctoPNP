$(function() {
    function OctoPNPSettingsViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];
        self.control = parameters[1];
        self.connection = parameters[2];

        self._headCanvas = document.getElementById('headCanvas');

        self.objectPositionX = ko.observable(0.0);
        self.objectPositionY = ko.observable(0.0);

        self.offsetCorrectionX = ko.observable(0.0);
        self.offsetCorrectionY = ko.observable(0.0);
        self.jogDistance = ko.observable(1.0);

        self.isConnected = ko.computed(function() {
            return self.connection.isOperational() || self.connection.isReady() || self.connection.isPaused();
        });

        self.statusCameraOffset = ko.observable(false);

        self.keycontrolPossible = ko.observable(false);
        self.keycontrolActive = ko.observable(false);
        self.showKeycontrols = ko.observable(true);
        self.keycontrolHelpActive = ko.observable(true);


        // This will get called before the ViewModel gets bound to the DOM, but after its depedencies have
        // already been initialized. It is especially guaranteed that this method gets called _after_ the settings
        // have been retrieved from the OctoPrint backend and thus the SettingsViewModel been properly populated.
        self.onBeforeBinding = function() {
            self.settings = self.settings.settings;
        };

        // Calibrate offset between primary extruder and head-camera
        self.cameraOffset = function() {
            self.statusCameraOffset(true);

            // Switch to primary extruder
            self.control.sendCustomCommand({command: "T0"});

            //move camera to object
            var x = self.objectPositionX() - self.settings.plugins.OctoPNP.camera.head.x();
            var y = self.objectPositionY() - self.settings.plugins.OctoPNP.camera.head.y();
            self.control.sendCustomCommand({command: "G1 X" + x + " Y" + y + " Z" + self.settings.plugins.OctoPNP.camera.head.z() + " F3000"});

            //reset offset correction values
            self.offsetCorrectionX(0.0);
            self.offsetCorrectionY(0.0);

            //activate Keycontrol
            self.keycontrolPossible(true);

            //trigger immage fetching
            setTimeout(function() {self._getImage('HEAD');}, 5000);
        }

        self.saveCameraOffset = function() {
            //save values...

            //deactivate Keycontrol
            self.keycontrolPossible(false);
            self.statusCameraOffset(false);
        }

        self.requestImage = function() {
            self._getImage("HEAD");
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
                        self._drawHeadImage(response.src);
                    }
                    if(response.hasOwnProperty("error")) {
                        alert(response.error);
                    }
                    if (callback) callback();
                }
            });
        };

        self._drawHeadImage = function(img) {
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
                    self.offsetCorrectionX(self.offsetCorrectionX()-self.jogDistance());
                    refreshImage = true;
                    break;
                case 38: // up arrow key
                    // Y+
                    self.control.sendJogCommand("y", 1, self.jogDistance());
                    self.offsetCorrectionY(self.offsetCorrectionY()+self.jogDistance());
                    refreshImage = true;
                    break;
                case 39: // right arrow key
                    // X+
                    self.control.sendJogCommand("x", 1, self.jogDistance());
                    self.offsetCorrectionX(self.offsetCorrectionX()+self.jogDistance());
                    refreshImage = true;
                    break;
                case 40: // down arrow key
                    // Y-
                    self.control.sendJogCommand("y", -1, self.jogDistance());
                    self.offsetCorrectionY(self.offsetCorrectionY()-self.jogDistance());
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
                setTimeout(function() {self._getImage('HEAD');}, 200);
            }
        };
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
