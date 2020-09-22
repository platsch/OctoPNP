//draw part and name at given position on the canvas
function drawPart(part, canvas, posX, posY, textPosX, textPosY, scale, color, rotation) {
	if (canvas && canvas.getContext) {
        var ctx = canvas.getContext("2d");
        if (ctx) {

            //print part name
            var font = Math.floor(2*scale).toString() + "px Verdana";
            ctx.font = font;
			ctx.fillStyle = "#000000";
			ctx.textBaseline = "top";
			ctx.fillText(part.name, textPosX, textPosY);

            // rotate part (everything drawn to canvas from this point will be rotated)
            ctx.translate(posX, posY);
            ctx.rotate(rotation);

			//draw part shapes
			if( part.hasOwnProperty("shape") ) {
				var points = part.shape;

				ctx.beginPath();
				ctx.strokeStyle = color;
				ctx.lineWidth = 1;
				ctx.fillStyle = color;
				if(points.length > 0) {
					ctx.moveTo(points[0][0]*scale, -points[0][1]*scale);
					for(var i=0; i < points.length; i++) {
						ctx.lineTo(points[i][0]*scale, -points[i][1]*scale);
					}
					//close loop
					ctx.lineTo(points[0][0]*scale, -points[0][1]*scale);
					ctx.lineTo(points[1][0]*scale, -points[1][1]*scale);
					ctx.fill();
				}
			}

			//draw part pads
			if( part.hasOwnProperty("pads") ) {
				var pads = part.pads;

				ctx.beginPath();
				ctx.fillStyle = "#999999";
				for(var i=0; i < pads.length; i++) {
					ctx.fillRect(pads[i][0]*scale, -pads[i][1]*scale, (pads[i][2]-pads[i][0])*scale, -(pads[i][3]-pads[i][1])*scale);
				}
			}
            ctx.rotate(-rotation);
            ctx.translate(-posX, -posY);
        }
    }
}
