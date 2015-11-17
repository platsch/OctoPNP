function smdTray(cols, rows, boxSize, canvas) {
	var self = this;

	self.cols = cols;
    self.rows = rows;
    self.trayBoxSize = boxSize;
    self.trayCanvas = canvas;
    self.parts = {};


	self.drawTray = function() {
		if (self.trayCanvas && self.trayCanvas.getContext) {
            var ctx = self.trayCanvas.getContext("2d");
            if (ctx) {
                var size_x = ctx.canvas.width;
                var size_y = ctx.canvas.height;
                var canvasBoxSize = self.getCanvasBoxSize();

                //initialize white tray
                ctx.strokeStyle = "black";
                ctx.fillStyle = "white";
                ctx.lineWidth = 1;
                ctx.fillRect(0,0,size_x,size_y);
                ctx.strokeRect (0,0,size_x,size_y);

				for(var x=0; x<self.cols; x++) {
                    for(var y=0; y<self.rows; y++) {
                        self.drawTrayBox(x, y, canvasBoxSize);
                    }
                }
            }
        }
	}
	
	
	//draw a part into a tray box
    self.drawPart = function(part) {
        console.log(part.name);
        var row = parseInt(((part.partPosition-1) / self.cols)) + 1;
		var col = (part.partPosition-1) % self.cols+1;

		//clear old box
		var canvasBoxSize = self.getCanvasBoxSize();
		self.drawTrayBox(col-1, row-1, canvasBoxSize);

		if (self.trayCanvas && self.trayCanvas.getContext) {
            var ctx = self.trayCanvas.getContext("2d");
            var scale = canvasBoxSize/self.trayBoxSize;
            if (ctx) {
                var col_offset = col*canvasBoxSize-canvasBoxSize+4;
                var row_offset = self.rows*canvasBoxSize-row*canvasBoxSize+4;

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
					ctx.lineWidth = 1;
					ctx.fillStyle = "#000000";
					if(points.length > 0) {
						ctx.moveTo(points[0][0]*scale+col_offset+canvasBoxSize/2, points[0][1]*scale+row_offset+canvasBoxSize/2);
						for(var i=0; i < points.length; i++) {
							ctx.lineTo(points[i][0]*scale+col_offset+canvasBoxSize/2, points[i][1]*scale+row_offset+canvasBoxSize/2);
						}
						//close loop
						ctx.lineTo(points[0][0]*scale+col_offset+canvasBoxSize/2, points[0][1]*scale+row_offset+canvasBoxSize/2);
						ctx.lineTo(points[1][0]*scale+col_offset+canvasBoxSize/2, points[1][1]*scale+row_offset+canvasBoxSize/2);
						ctx.fill();
					}
				}

				//draw part pads
				if( part.hasOwnProperty("pads") ) {
					var pads = part.pads;

					ctx.beginPath();
					ctx.fillStyle = "#999999";
					for(var i=0; i < pads.length; i++) {
						ctx.fillRect(pads[i][0]*scale+col_offset+canvasBoxSize/2, pads[i][1]*scale+row_offset+canvasBoxSize/2, (pads[i][2]-pads[i][0])*scale, (pads[i][3]-pads[i][1])*scale);
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
                ctx.strokeRect (col*size+ctx.lineWidth/2,(self.rows-1)*size-row*size+ctx.lineWidth/2,size-ctx.lineWidth/2,size-ctx.lineWidth/2);
                ctx.fillRect (col*size+ctx.lineWidth,(self.rows-1)*size-row*size+ctx.lineWidth,size-ctx.lineWidth,size-ctx.lineWidth);
            }
        }
    }

    self.getCanvasBoxSize = function() {
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
}
