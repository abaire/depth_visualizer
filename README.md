# depth_visualizer
Trivial tkinter app to render and retrieve values from raw depth maps.

Usage:

Open a raw depth buffer (8-bpp, 16-bpp, and 24-bpp in z24s8 format are supported) using the File menu.
Hover and/or click on a pixel to view its actual value in the footer.

Visualization can be changed with the "View" menu.
* RGB - Render as RGB (except 8-bpp which is always greyscale). The low order byte will be the red channel, then green, etc...
* Greyscale - Render as greyscale, normalized to the full greyscale range (i.e., each pixel will be divided by the maximum possible value for the bitdepth. E.g., 0xFFFF for 16-bpp)
* Greyscale: stretched - Render as greyscale, stretching the actually used values across the range 0 - 1 (the pixel with the lowest (nearest) value will become the darkest, the pixel with the highest (farthest) value will become the lightest).
