G28
G1 X10 F3000
G1 Y250 F3000
G1 Z10 F3000

M361 P1
;M361 P2
;M361 P3
;<object name="simple_lines">
;<part id="1" name="LED_1206">
;  <position box="4"/>
;  <size height="1.05"/>
;  <shape>
;    <point x="value" y="value"/>
;    <point x="value2" y="value2"/>
;  </shape>
;  <pads>
;    <pad x1="-0.4" y1="-0.8" x2="0.1" y2="0.3"/>
;    <pad x1="-1.4" y1="-0.8" x2="-0.9" y2="0.3"/>
;  </pads>
;  <destination x="104.938" y="27.987" z="8.000" orientation="90"/>
;</part>


;<part id="2" name="RES_1206">
;  <position box="5"/>
;  <size height="0.5"/>
;  <shape>
;    <point x="value" y="value"/>
;    <point x="value2" y="value2"/>
;  </shape>
;  <pads>
;    <pad x1="-0.4" y1="-0.8" x2="0.1" y2="0.3"/>
;    <pad x1="-1.4" y1="-0.8" x2="-0.9" y2="0.3"/>
;  </pads>
;  <destination x="104.938" y="27.987" z="8.000" orientation="0"/>
;</part>

;<part id="3" name="Oscillator">
;  <position box="2"/>
;  <size height="1.05"/>
;  <shape>
;    <point x="value" y="value"/>
;    <point x="value2" y="value2"/>
;  </shape>
;  <pads>
;    <pad x1="-0.4" y1="-0.8" x2="0.1" y2="0.3"/>
;    <pad x1="-1.4" y1="-0.8" x2="-0.9" y2="0.3"/>
;  </pads>
;  <destination x="104.938" y="27.987" z="8.000" orientation="90"/>
;</part>

;<part id="4" name="ATTINY">
;  <position box="3"/>
;  <size height="1.95"/>
;  <shape>
;    <point x="0.1" y="1.5"/>
;    <point x="-2" y="0"/>
;  </shape>
;  <pads>
;    <pad x1="-0.4" y1="-0.8" x2="0.1" y2="0.3"/>
;    <pad x1="-1.4" y1="-0.8" x2="-0.9" y2="0.3"/>
;  </pads>
;  <destination x="90.938" y="20" z="8.000" orientation="45"/>
;</part>
;</object>

