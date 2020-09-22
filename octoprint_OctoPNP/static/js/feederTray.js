function feederTray(partlist, trayConfiguration, canvas) {
    var self = this;

    var _parts = partlist;
    var _trayConfiguration = trayConfiguration;
    var _trayCanvas = canvas;

    // internal configuration
    var _labelOffset = 40; // leave some space at the left side for row number labels
    var _rowLineWidth = 3; // thicker lines between rows


    self.render = function() {
        self._drawTray();
        for (var i in _parts()) {
            self._drawPart(_parts()[i], "black");
        }
    }

    self.selectPart = function(x, y) {
        var scale = self._getCanvasScaling();
        var partId = undefined;
        self.render();
        // find col and row
        var y_offset = _rowLineWidth;
        for(var row = _trayConfiguration.length - 1; row >= 0; row--) {
            if((y > y_offset) && (y < y_offset + parseInt(_trayConfiguration[row].width())*scale)) {
                col = Math.floor((x - _labelOffset) / (parseInt(_trayConfiguration[row].spacing())*scale));

                // find matching part
                for (var i in _parts()) {
                    if((_parts()[i].col == col) && (_parts()[i].row == row)) {
                        self._drawPart(_parts()[i], "red");
                        partId = _parts()[i].id;
                        break;
                    }
                }
                break;
            }
            y_offset += parseInt(_trayConfiguration[row].width())*scale;
        }

        return partId;
    }


    self._drawTray = function() {
        if (_trayCanvas && _trayCanvas.getContext) {
            var ctx = _trayCanvas.getContext("2d");
            if (ctx) {
                var size_x = ctx.canvas.width;
                var size_y = ctx.canvas.height;
                var scale = self._getCanvasScaling();

                //initialize white tray
                ctx.font = "16px Verdana";
                ctx.textBaseline = "middle";
                ctx.strokeStyle = "black";
                ctx.fillStyle = "white";
                ctx.lineWidth = 1;
                ctx.fillRect(0,0,size_x,size_y);
                ctx.strokeRect (0,0,size_x,size_y);

                var rowPos = _rowLineWidth;
                for(var row = _trayConfiguration.length - 1; row >= 0; row--) {
                    ctx.lineWidth = _rowLineWidth;
                    // how many components would fit into this row?
                    var width = parseInt(_trayConfiguration[row].width())*scale;
                    var spacing = parseInt(_trayConfiguration[row].spacing())*scale;

                    // label
                    ctx.fillStyle = "black";
                    ctx.fillText(row.toString(), 8, rowPos + width/2);
                    ctx.fillStyle = "white";

                    var cols = Math.floor((size_x - _labelOffset - _rowLineWidth) / spacing);
                    // draw the row
                    ctx.fillRect(_labelOffset, rowPos, cols*spacing, width);
                    ctx.strokeRect (_labelOffset, rowPos, cols*spacing, width);

                    // draw slots
                    for(var col = 0; col < cols; col++) {
                        ctx.lineWidth = 1;
                        ctx.strokeRect (_labelOffset+col*spacing, rowPos, spacing, width);
                        ctx.fillRect (_labelOffset+col*spacing, rowPos, spacing, width);
                    }

                    rowPos += width;
                }
            }
        }
    }
    
    //draw a part into a tray box
    self._drawPart = function(part, color) {
        if((part.row >= 0) && (part.col >= 0)) {
            var scale = self._getCanvasScaling();

            // compute row position for this part
            var y_offset = _rowLineWidth;
            var x_offset = _labelOffset;
            for(var row = _trayConfiguration.length - 1; row >= 0; row--) {
                if(row <= part.row) {
                    x_offset += part.col * parseInt(_trayConfiguration[row].spacing())*scale;
                    var rotation = Math.PI/180 * parseInt(_trayConfiguration[row].rotation());
                    // use function fom trayUtil.js to actually draw the component
                    drawPart(part, _trayCanvas, x_offset + 0.5 * parseInt(_trayConfiguration[row].spacing()) * scale, y_offset + 0.5 * parseInt(_trayConfiguration[row].width()) * scale, x_offset, y_offset, scale, color, rotation);
                    break;
                }
                y_offset += parseInt(_trayConfiguration[row].width())*scale;
            }
        }
    }

    // returns the box size to use the available canvas-space in an optimal way
    self._getCanvasScaling = function() {
        var scale = 0;
        if (_trayCanvas && _trayCanvas.getContext) {
            var ctx = _trayCanvas.getContext("2d");
            if (ctx) {
                var trayLength = 0;
                for (var i = 0; i < _trayConfiguration.length; i++) {
                    trayLength += parseInt(_trayConfiguration[i].width());
                }
                scale = (ctx.canvas.height - 2*_rowLineWidth) / trayLength;

                // should probably also check maximum width of the canvas, but max number of components in each tray row is currently not defined...
            }
        }
        return scale;
    }
}
