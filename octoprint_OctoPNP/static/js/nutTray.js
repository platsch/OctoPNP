function nutTray(cols, rows, boxSize, config, canvas) {
	var self = this;

	var _cols = cols;
	var _rows= rows;
	var _trayBoxSize = boxSize;
	var _trayCanvas = canvas;
	var _config = JSON.parse(config);
	var _parts = {};

	self.erase = function() {
		_parts = {};
		_drawTray();
	}

	self.addPart = function(part) {
		// sanitiy checks!?
		// add part to dict
		_parts[part.id] = part;

		_parts[part.id].row = parseInt(((part.partPosition) / _cols)) + 1;
		_parts[part.id].col = (part.partPosition) % _cols + 1;

		// and draw to canvas
		_drawPart(part.id, part.threadSize, part.type, "#aaa");
	}

	self.selectPart = function(x, y) {
		var canvasBoxSize = _getCanvasBoxSize();
		col = Math.floor(x/(canvasBoxSize+1)) + 1;
		row = Math.floor(((_rows*canvasBoxSize)-y)/(canvasBoxSize-1)) + 1;

		for (var id in _parts) {
			_drawPart(id, _parts[id].threadSize, _parts[id].type, "#aaa");
		}

		var partId = _getPartId(col, row);
		if(partId) {
			_drawPart(partId, _parts[partId].threadSize, _parts[partId].type, "red");
		}
		return partId;
	}


	function _drawTray () {
		if (_trayCanvas && _trayCanvas.getContext) {
			var ctx = _trayCanvas.getContext("2d");
			if (ctx) {
				var size_x = ctx.canvas.width;
				var size_y = ctx.canvas.height;
				var canvasBoxSize = _getCanvasBoxSize();

				//initialize white tray
				ctx.strokeStyle = "black";
				ctx.fillStyle = "white";
				ctx.lineWidth = 1;
				ctx.fillRect(0,0,size_x,size_y);
				ctx.strokeRect (0,0,size_x,size_y);

				for(var x = 0; x < _rows; x++) {
					for(var y = 0; y < _cols; y++) {
						_drawTrayBox(y + 1, x + 1, canvasBoxSize);
					}
				}
			}
		}
	}


	//draw a part into a tray box
	function _drawPart(partID, threadSize, type, color) {
		part = _parts[partID];

		//clear old box
		var canvasBoxSize = _getCanvasBoxSize();
		_drawTrayBox(part.col, part.row, canvasBoxSize);

		if (_trayCanvas && _trayCanvas.getContext) {
			var ctx = _trayCanvas.getContext("2d");
			var scale = canvasBoxSize/_trayBoxSize;
			if (ctx) {
				var col_offset = part.col*canvasBoxSize-canvasBoxSize+4;
				var row_offset = _rows*canvasBoxSize-part.row*canvasBoxSize+4;

				//print part names
				ctx.font = "8px Verdana";
				ctx.fillStyle = "#000000";
				ctx.textBaseline = "top";
				ctx.fillText("partnr " + part.id, col_offset, row_offset + canvasBoxSize - 16);

				partOutlineSize = (partSize * 5 + 3) * (canvasBoxSize / 100)
				// let size = parseFloat(threadSize) * 5;
				let size = partOutlineSize;
				x = (part.col - 1) * canvasBoxSize + 4 / 2 + canvasBoxSize / 2;
				y = _rows * canvasBoxSize - (part.row - 1) * canvasBoxSize + 4 / 2 - canvasBoxSize / 2;

				ctx.fillStyle = color;
				ctx.beginPath();
				if (slotOrientation === "flat") {
					if (type === "hexnut") {
						for (let i = 0; i < 360; i += 60) {
							ctx.lineTo(x + Math.sin(i * Math.PI / 180) * size * 0.45, y + Math.cos(i * Math.PI / 180) * size * 0.45);
						}
					}
					else if (type === "squarenut") {
						ctx.lineTo(x - size / 2, y -  size / 2);
						ctx.lineTo(x +  size / 2,y - size / 2);
						ctx.lineTo(x + size / 2,y + size / 2);
						ctx.lineTo(x - size / 2, y + size / 2);
					}
					ctx.closePath();
					ctx.fill();

					ctx.beginPath();
					ctx.fillStyle = "white";
					ctx.arc(x, y, size / 7.0, 0, 2 * Math.PI);
					ctx.fill();
					ctx.closePath();
				} else if (slotOrientation === "upright") {
					if (type === "hexnut") {
						ctx.beginPath();
						ctx.lineTo(x + partOutlineSize / 6, y - partOutlineSize / 2);
						ctx.lineTo(x + partOutlineSize / 6, y + partOutlineSize / 2);
						ctx.lineTo(x - partOutlineSize / 6, y + partOutlineSize / 2);
						ctx.lineTo(x - partOutlineSize / 6, y - partOutlineSize / 2);
						ctx.closePath();
						ctx.fill();

						ctx.beginPath();
						ctx.moveTo(x - partOutlineSize / 6, y + partOutlineSize / 4);
						ctx.lineTo(x + partOutlineSize / 6, y + partOutlineSize / 4);
						ctx.moveTo(x - partOutlineSize / 6, y - partOutlineSize / 4);
						ctx.lineTo(x + partOutlineSize / 6, y - partOutlineSize / 4);
						ctx.stroke();
					} else if (type === "squarenut") {
						ctx.beginPath();
						ctx.lineTo(x + partOutlineSize / 6, y - partOutlineSize / 2);
						ctx.lineTo(x + partOutlineSize / 6, y + partOutlineSize / 2);
						ctx.lineTo(x - partOutlineSize / 6, y + partOutlineSize / 2);
						ctx.lineTo(x - partOutlineSize / 6, y - partOutlineSize / 2);
						ctx.fill();
					}
				}


			}
		}
	}

	// draw a single tray box
	function _drawTrayBox(col, row, size) {
		col -=1;
		row -=1;
		if (_trayCanvas && _trayCanvas.getContext) {
			var ctx = _trayCanvas.getContext("2d");
			if (ctx) {
				var canvasBoxSize = _getCanvasBoxSize();
				ctx.lineWidth = 1;
				ctx.strokeStyle = "black";
				ctx.fillStyle = "white";
				ctx.strokeRect (col*size+ctx.lineWidth/2,(_rows-1)*size-row*size+ctx.lineWidth/2,size-ctx.lineWidth/2,size-ctx.lineWidth/2);
				ctx.fillRect (col*size+ctx.lineWidth,(_rows-1)*size-row*size+ctx.lineWidth,size-ctx.lineWidth,size-ctx.lineWidth);
				x = col * size + ctx.lineWidth / 2 + size / 2 + 1.5;
				y = (_rows - 1) * size - row * size + ctx.lineWidth / 2 + size / 2 + 1.5;

				nutShape = _config[(parseInt(row)) * parseInt(_cols) + parseInt(col)].nut
				partSize = _config[(parseInt(row)) * parseInt(_cols) + parseInt(col)].thread_size
				slotOrientation = _config[(parseInt(row)) * parseInt(_cols) + parseInt(col)].slot_orientation
				partOutlineSize = (partSize * 5 + 3) * (canvasBoxSize / 100)

				ctx.beginPath();
				ctx.fillStyle = '#888';
				ctx.font = "8px Verdana";
				ctx.fillText("M" + partSize + " " + nutShape.replace("nut",""), x - canvasBoxSize / 2.0 + 4, y - canvasBoxSize / 2.0 + 10);
				ctx.fillText(slotOrientation, x - canvasBoxSize / 2.0 + 4, y - canvasBoxSize / 2.0 + 18);
				ctx.fillStyle = '#000';
				if (nutShape === "hexnut") {
					if (slotOrientation === "flat") {
						for (let i = 0; i < 360; i += 60) {
							ctx.lineTo(x + Math.sin(i * Math.PI / 180) * partOutlineSize * 0.45, y + Math.cos(i * Math.PI / 180) * partOutlineSize * 0.45);
						}
					} else if (slotOrientation === "upright") {
						ctx.moveTo(x - partOutlineSize / 6, y + partOutlineSize / 4);
						ctx.lineTo(x + partOutlineSize / 6, y + partOutlineSize / 4);
						ctx.moveTo(x - partOutlineSize / 6, y - partOutlineSize / 4);
						ctx.lineTo(x + partOutlineSize / 6, y - partOutlineSize / 4);

						ctx.moveTo(x - partOutlineSize / 6, y - partOutlineSize / 2);
						ctx.lineTo(x + partOutlineSize / 6, y - partOutlineSize / 2);
						ctx.lineTo(x + partOutlineSize / 6, y + partOutlineSize / 2);
						ctx.lineTo(x - partOutlineSize / 6, y + partOutlineSize / 2);
						ctx.lineTo(x - partOutlineSize / 6, y - partOutlineSize / 2);
					}
				} else if (nutShape === "squarenut") {
					if (slotOrientation === "flat") {
						ctx.lineTo(x - partOutlineSize / 2, y - partOutlineSize / 2);
						ctx.lineTo(x + partOutlineSize / 2, y - partOutlineSize / 2);
						ctx.lineTo(x + partOutlineSize / 2, y + partOutlineSize / 2);
						ctx.lineTo(x - partOutlineSize / 2, y + partOutlineSize / 2);
					} else if (slotOrientation === "upright") {
						ctx.lineTo(x + partOutlineSize / 6, y - partOutlineSize / 2);
						ctx.lineTo(x + partOutlineSize / 6, y + partOutlineSize / 2);
						ctx.lineTo(x - partOutlineSize / 6, y + partOutlineSize / 2);
						ctx.lineTo(x - partOutlineSize / 6, y - partOutlineSize / 2);
					}
				}
				ctx.closePath();
				ctx.lineWidth = 1;
				ctx.stroke();
			}
		}
	}

	// returns the box size to use the available canvas-space in an optimal way
	function _getCanvasBoxSize() {
		var boxSize = 0;
		if (_trayCanvas && _trayCanvas.getContext) {
			var ctx = _trayCanvas.getContext("2d");
			if (ctx) {
				var size_x = ctx.canvas.width;
				var size_y = ctx.canvas.height;
				boxSize = Math.min((size_x-4)/_cols, (size_y-4)/_rows);
			}
		}
		return Math.floor(boxSize);
	}

	// select partId from col/row
	function _getPartId(col, row) {
		var result = false;
		for (var id in _parts) {
			if((_parts[id].col == col) && (_parts[id].row == row)) {
				result = id;
				break;
			}
		}
		return result;
	}
}

