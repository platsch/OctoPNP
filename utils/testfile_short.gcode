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
;    <point x="-1.5" y="0.75"/>
;    <point x="1.5" y="0.75"/>
;    <point x="1.5" y="-0.75"/>
;    <point x="-1.5" y="-0.75"/>
;  </shape>
;  <pads>
;    <pad x1="-1.5" y1="0.75" x2="-1.1" y2="-0.75"/>
;    <pad x1="1.5" y1="0.75" x2="1.1" y2="-0.75"/>
;  </pads>
;  <destination x="104.938" y="27.987" z="8.000" orientation="90"/>
;</part>


;<part id="2" name="RES_1206">
;  <position box="5"/>
;  <size height="0.5"/>
;  <shape>
;    <point x="-1.5" y="0.75"/>
;    <point x="1.5" y="0.75"/>
;    <point x="1.5" y="-0.75"/>
;    <point x="-1.5" y="-0.75"/>
;  </shape>
;  <pads>
;    <pad x1="-1.5" y1="0.75" x2="-1.1" y2="-0.75"/>
;    <pad x1="1.5" y1="0.75" x2="1.1" y2="-0.75"/>
;  </pads>
;  <destination x="104.938" y="27.987" z="8.000" orientation="0"/>
;</part>

;<part id="3" name="Oscillator">
;  <position box="2"/>
;  <size height="1.05"/>
;  <shape>
;    <point x="-1.1" y="1"/>
;    <point x="1.1" y="1"/>
;    <point x="1.1" y="-1"/>
;    <point x="-1.1" y="-1"/>
;  </shape>
;  <pads>
;    <pad x1="-0.4" y1="-0.8" x2="0.1" y2="0.3"/>
;    <pad x1="-1.4" y1="-0.8" x2="-0.9" y2="0.3"/>
;  </pads>
;  <destination x="104.938" y="27.987" z="8.000" orientation="90"/>
;</part>

;<part id="4" name="Attiny">
;  <position box="3"/>
;  <size height="1.95"/>
;  <shape>
;    <point x="-2.55" y="2.65"/>
;    <point x="2.55" y="2.65"/>
;    <point x="2.55" y="-2.65"/>
;    <point x="-2.55" y="-2.65"/>
;  </shape>
;  <pads>
;    <pad x1="-2.08" y1="4.0" x2="1.68" y2="3.3"/>
;    <pad x1="-0.81" y1="4.0" x2="0.41" y2="3.3"/>
;    <pad x1="0.46" y1="4.0" x2="0.81" y2="3.3"/>
;    <pad x1="1.73" y1="4.0" x2="2.13" y2="3.3"/>
;    <pad x1="-2.08" y1="-3.3" x2="1.68" y2="-4.0"/>
;    <pad x1="-0.81" y1="-3.3" x2="0.41" y2="-4.0"/>
;    <pad x1="0.46" y1="-3.3" x2="0.81" y2="-4.0"/>
;    <pad x1="1.73" y1="-3.3" x2="2.13" y2="-4.0"/>
;  </pads>
;  <destination x="90.938" y="20" z="8.000" orientation="45"/>
;</part>
;</object>

