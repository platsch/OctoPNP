$(function() {
    function OctoPNPViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];


        self.stateString = ko.observable("No file loaded");
        self.currentOperation = ko.observable("");
        self.cameraImage = ko.observable("testfile");
        self.debugvar = ko.observable("a");

        // This will get called before the HelloWorldViewModel gets bound to the DOM, but after its depedencies have
        // already been initialized. It is especially guaranteed that this method gets called _after_ the settings
        // have been retrieved from the OctoPrint backend and thus the SettingsViewModel been properly populated.
        self.onBeforeBinding = function() {
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
                else if(data.event == "IMAGE") {
                    //self.cameraImage(data.data.src);
                }
                self.debugvar("Plugin = OctoPNP");
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
        [document.getElementById("tab_plugin_OctoPNP")]
    ]);
});
