s = 3.5;

translate([-30,-4,0]){
	scale(s)
	translate([0,-26,0])
	{
		linear_extrude(height=2/s)
		import("chaveiro-w3c.dxf", layer="borda");

		linear_extrude(height=3/s)
		import("chaveiro-w3c.dxf", layer="argola");

		linear_extrude(height=1/s)
		import("chaveiro-w3c.dxf", layer="w3c");
	}

	%cube([59.7, 31.4, 0.1]);
}