function boxTray(partlist, cols, rows, boxSize, canvas) {
	var self = this;

	var _cols = cols;
    var _rows= rows;
    var _trayBoxSize = boxSize;
    var _trayCanvas = canvas;
    var _parts = partlist;


    self.render = function() {
        _drawTray();
        for (var i in _parts()) {
            _drawPart(_parts()[i].id, "black");
        }
    }

    self.selectPart = function(x, y) {
        var canvasBoxSize = _getCanvasBoxSize();
        col = Math.floor(x/(canvasBoxSize+1)) + 1;
        row = Math.floor(((_rows*canvasBoxSize)-y)/(canvasBoxSize-1)) + 1;

        self.render();

        var partId = _getPartId(col, row);
        if(partId) {
            _drawPart(partId, "red");
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

				for(var x=0; x<_cols; x++) {
                    for(var y=0; y<_rows; y++) {
                        _drawTrayBox(x+1, y+1, canvasBoxSize);
                    }
                }
            }
        }
	}
	
	
	//draw a part into a tray box
    function _drawPart(partID, color) {
        // find part with partID in array
        var part;
        for (var i in _parts()) {
            if(_parts()[i].id == partID) {
                part = _parts()[i];
            }
        }

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
				ctx.font = "10px Verdana";
				ctx.fillStyle = "#000000";
				ctx.textBaseline = "top";
				ctx.fillText(part.name, col_offset, row_offset);

				//draw part shapes
				if( part.hasOwnProperty("shape") ) {
					var points = part.shape;

					ctx.beginPath();
					ctx.strokeStyle = color;
					ctx.lineWidth = 1;
					ctx.fillStyle = color;
					if(points.length > 0) {
						ctx.moveTo(points[0][0]*scale+col_offset+canvasBoxSize/2, -points[0][1]*scale+row_offset+canvasBoxSize/2);
						for(var i=0; i < points.length; i++) {
							ctx.lineTo(points[i][0]*scale+col_offset+canvasBoxSize/2, -points[i][1]*scale+row_offset+canvasBoxSize/2);
						}
						//close loop
						ctx.lineTo(points[0][0]*scale+col_offset+canvasBoxSize/2, -points[0][1]*scale+row_offset+canvasBoxSize/2);
						ctx.lineTo(points[1][0]*scale+col_offset+canvasBoxSize/2, -points[1][1]*scale+row_offset+canvasBoxSize/2);
						ctx.fill();
					}
				}

				//draw part pads
				if( part.hasOwnProperty("pads") ) {
					var pads = part.pads;

					ctx.beginPath();
					ctx.fillStyle = "#999999";
					for(var i=0; i < pads.length; i++) {
						ctx.fillRect(pads[i][0]*scale+col_offset+canvasBoxSize/2, -pads[i][1]*scale+row_offset+canvasBoxSize/2, (pads[i][2]-pads[i][0])*scale, -(pads[i][3]-pads[i][1])*scale);
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
                ctx.lineWidth = 4;
                ctx.strokeStyle = "green";
                ctx.fillStyle = "white";
                ctx.strokeRect (col*size+ctx.lineWidth/2,(_rows-1)*size-row*size+ctx.lineWidth/2,size-ctx.lineWidth/2,size-ctx.lineWidth/2);
                ctx.fillRect (col*size+ctx.lineWidth,(_rows-1)*size-row*size+ctx.lineWidth,size-ctx.lineWidth,size-ctx.lineWidth);
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
        for (var i in _parts()) {
            if((_parts()[i].col == col) && (_parts()[i].row == row)) {
                result = _parts()[i].id;
                break;
            }
        }
        return result;
    }
}
