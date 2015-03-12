$(function() {
    function OctoPNPViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];

        self.tray = {}
        self.camera = []
        self.nozzle = {}

        self.stateString = ko.observable("No file loaded");
        self.currentOperation = ko.observable("");
        self.cameraImage = ko.observable("testfile");
        self.debugvar = ko.observable("a");

        // This will get called before the HelloWorldViewModel gets bound to the DOM, but after its depedencies have
        // already been initialized. It is especially guaranteed that this method gets called _after_ the settings
        // have been retrieved from the OctoPrint backend and thus the SettingsViewModel been properly populated.
        self.onBeforeBinding = function() {
            self.tray = self.settings.settings.plugins.OctoPNP.tray;
            self.camera = self.settings.settings.plugins.OctoPNP.camera;
            self.nozzle = self.settings.settings.plugins.OctoPNP.nozzle;
        }

         self.onDataUpdaterPluginMessage = function(plugin, data) {
            if(plugin == "OctoPNP") {
                if(data.event == "FILE") {
                    if(data.data.hasOwnProperty("parts")) {
                        self.stateString("Loaded file with " + data.data.parts + " SMD parts");
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
                else if(data.event == "IMAGE") {
                    //self.cameraImage(data.data.src);
                }
                self.debugvar("Plugin = OctoPNP");
            }
        };

        self.removeCamera = function(cam) {
            self.camera.remove(cam);
        }

        self.addCamera = function() {
            self.camera.push({x: 0, y: 0, z: 0, name: "New Camera"});
        }
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
