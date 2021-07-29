$(function() {
	function OctoPNPViewModel(parameters) {
		var self = this;

		self.settings = parameters[0];
		self.control = parameters[1];
		self.connection = parameters[2];

		self.parts = ko.observableArray([]); // list of parts in the current file, includes tray assignments);
		self.trayfeeder_rows = ko.observableArray([]); // list of available trayfeeder rows for dropdown list in assignment table

		var _boxTray = {};
		var _feederTray = {};
		var _nutTray = {};
		var _trayCanvas = document.getElementById('trayCanvas');

		self.stateString = ko.observable("No file loaded");
		self.currentOperation = ko.observable("");
		self.debugvar = ko.observable("");

		self.assignComponentsDialog = ko.observable(false);

		//white placeholder images
		document.getElementById('headCameraImage').setAttribute( 'src', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3wMRCQAfAmB4CgAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAAAMSURBVAjXY/j//z8ABf4C/tzMWecAAAAASUVORK5CYII=');
		document.getElementById('bedCameraImage').setAttribute( 'src', 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3wMRCQAfAmB4CgAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAAAMSURBVAjXY/j//z8ABf4C/tzMWecAAAAASUVORK5CYII=');


		// This will get called before the ViewModel gets bound to the DOM, but after its depedencies have
		// already been initialized. It is especially guaranteed that this method gets called _after_ the settings
		// have been retrieved from the OctoPrint backend and thus the SettingsViewModel been properly populated.
		self.onBeforeBinding = function() {
			self.traySettings = self.settings.settings.plugins.OctoPNP.tray;
			_boxTray = new boxTray(
				self.parts,
				self.traySettings.box.columns(),
				self.traySettings.box.rows(),
				self.traySettings.box.boxsize(),
				_trayCanvas
			);
			_feederTray = new feederTray(
				self.parts,
				self.traySettings.feeder.feederconfiguration(),
				_trayCanvas
			);
			_nutTray = new nutTray(
				self.parts,
				self.traySettings.nut.columns(),
				self.traySettings.nut.rows(),
				self.traySettings.nut.boxsize(),
				_trayCanvas
			);
			_trayCanvas.addEventListener("click", self.onSmdTrayClick, false); //"click, dblclick"
			_trayCanvas.addEventListener("dblclick", self.onSmdTrayDblclick, false); //"click, dblclick"
		}

		self.toggleAssignComponentsDialog = function() {
			self.assignComponentsDialog(!self.assignComponentsDialog());
		}

		// this is a workaround to notifiy the assignment table about changes inside the objects hold by the observableArray.
		// It is probably a very bad (computationally expensive) solution, but at some point I just didn't want to waste any more time on this.
		self.trayFeederChange = function(item) {
			self.parts.remove(item);

			// update col
			if(item.row < 0) {
				item.col = -1;
			} else {
				var cols = [];
				for(var i=0; i < self.parts().length; i++) {
					if(self.parts()[i].row == item.row) {
						cols.push(self.parts()[i].col);
					}
				}
				var col = 0;
				var done = false;
				while(!done) {
					done = true;
					for(var i=0; i < cols.length; i++) {
						if(cols[i] == col) {
							col++;
							done = false;
							break;
						}
					}
				}
				item.col = col;
			}

			self.parts.push(item);
			self.parts.sort(function (a, b) {return a.id < b.id ? -1 : 1;});

			// update mapping in plugin backend
			mapping = {};
			for(var i=0; i < self.parts().length; i++) {
				mapping[self.parts()[i].id] = {"row": self.parts()[i].row, "col": self.parts()[i].col}
			}
			self._pushTrayAssignments(mapping);

			_feederTray.render();
		}

		// catch mouseclicks at the tray for interactive part handling
		self.onSmdTrayClick = function(event) {
			var rect = _trayCanvas.getBoundingClientRect();
			var x = Math.floor(event.clientX - rect.left);
			var y = Math.floor(event.clientY - rect.top);
			var result = undefined;
			if(self.traySettings.type() == "BOX") {
				result = _boxTray.selectPart(x, y);
			}
			else if(self.traySettings.type() == "FEEDER") {
				result = _feederTray.selectPart(x, y);
			}
			else if(self.traySettings.type() == "NUT") {
				result = _nutTray.selectPart(x, y);
			}
			return result;
		}

		self.onSmdTrayDblclick = function(event) {
			// highlight part on tray and find partId
			var partId = self.onSmdTrayClick(event);

			// execute pick&place operation
			if(partId) {
				// printer connected and not printing?
				if(self.connection.isOperational() || self.connection.isReady()) {
					self.control.sendCustomCommand({ command: "M361 P" + partId});
				}
			}
		}


		// receive updates from plugin backend
		self.onDataUpdaterPluginMessage = function(plugin, data) {
			if(plugin == "OctoPNP") {
				if(data.event == "FILE") {
					self.parts([]);  // reset component list
					var typeStr = "SMD"
					if ( self.traySettings.type() == "NUT" ) {
						typeStr = "Nut"
					}
					if(data.data.hasOwnProperty("partCount")) {
						self.stateString("Loaded file with " + data.data.partCount + " " + typeStr + " parts.");

						// init feeder configuration
						if(self.traySettings.type() == "FEEDER") {
							self.assignComponentsDialog(true); // show feeder assignment dialog
							self.trayfeeder_rows([{name: "-1", value: -1}]); // reset
							for(var i=0; i < self.traySettings.feeder.feederconfiguration().length; i++) {
								self.trayfeeder_rows.push({name: i.toString(), value: i});
							}
						}

						//extract part information
						if( data.data.hasOwnProperty("parts") ) {
							var parts = data.data.parts;
							for(var i=0; i < parts.length; i++) {
								// this is a completely absurd and weird workaround.
								// for reasons beyond my comprehension, the "row" field in parts dict is
								// set to undefined by knockout when pushing to the self.parts array.
								// Changing the field name to anything but "row" solves the problem.
								// I wanted to keep the name, so the value of row is stored and then updated after pushing to the array.
								var row = parts[i].row;
								self.parts.push(parts[i]);
								self.parts()[i].row = row;
							}
							if(self.traySettings.type() == "BOX") {
								_boxTray.render();
							}
							else if(self.traySettings.type() == "FEEDER") {
								_feederTray.render();
							}
							else if(self.traySettings.type() == "NUT") {
								_nutTray.render();
							}
						}
					}else{
						self.stateString("No " + typeStr + " parts in this file!");
					}
				}
				else if(data.event == "OPERATION") {
					self.currentOperation(data.data.type + " part nr " + data.data.part);
				}
				else if(data.event == "ERROR") {
					self.stateString("ERROR: \"" + data.data.type + "\"");
					if(data.data.hasOwnProperty("part")) {
						self.stateString(self.StateString + " appeared while processing part nr " + data.data.part);
					}
				}
				else if(data.event == "INFO") {
					self.stateString("INFO: \"" + data.data.type + "\"");
				}
				else if(data.event == "HEADIMAGE") {
					document.getElementById('headCameraImage').setAttribute( 'src', data.data.src );
				}
				else if(data.event == "BEDIMAGE") {
					document.getElementById('bedCameraImage').setAttribute( 'src', data.data.src );
				}
			}
		};

		self._pushTrayAssignments = function(mapping, callback) {
			$.ajax({
				url: PLUGIN_BASEURL + "OctoPNP/tray_assignments?mapping=" + JSON.stringify(mapping),
				type: "GET",
				dataType: "json",
				contentType: "application/json; charset=UTF-8",
				//data: JSON.stringify(mapping),
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
	}

	// This is how our plugin registers itself with the application, by adding some configuration information to
	// the global variable ADDITIONAL_VIEWMODELS
	ADDITIONAL_VIEWMODELS.push([
		// This is the constructor to call for instantiating the plugin
		OctoPNPViewModel,

		// This is a list of dependencies to inject into the plugin, the order which you request here is the order
		// in which the dependencies will be injected into your view model upon instantiation via the parameters
		// argument
		["settingsViewModel", "controlViewModel", "connectionViewModel"],

		// Finally, this is the list of all elements we want this view model to be bound to.
		"#tab_plugin_OctoPNP"
	]);
});
