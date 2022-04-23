#!/usr/bin/env python3

"""Utility to examine raw depth buffer values."""

import argparse
import struct
import sys
import tkinter
from tkinter import filedialog
from tkinter import simpledialog

from PIL import Image
from PIL import ImageTk

_UNPACK_PATTERN = {1: "B", 2: "<H", 4: "<L"}

_IMAGE_MODE = {"RGB": "RGB", "GREYSCALE": "GREYSCALE", "L_STRETCHED": "L_STRETCHED"}


class DepthImage:
    def __init__(self, filename, width, height, bpp):
        self.width = width
        self.height = height
        # 24 bit depth textures will have stencil bits in the low order byte.
        if bpp == 24:
            bpp = 32
        self.bpp = bpp
        self.bytes_per_pixel = bpp >> 3
        self.pitch = width * self.bytes_per_pixel

        with open(filename, "rb") as infile:
            self.image = infile.read()

    def value_at(self, x, y):
        offset = y * self.pitch + x * self.bytes_per_pixel
        try:
            value = struct.unpack(
                _UNPACK_PATTERN[self.bytes_per_pixel],
                self.image[offset : offset + self.bytes_per_pixel],
            )[0]
        except struct.error:
            return None
        return value

    def to_pil_image(self, view_mode):
        if self.bytes_per_pixel == 1:
            return Image.frombytes("L", (self.width, self.height), self.image)

        if self.bytes_per_pixel == 2:
            if view_mode == _IMAGE_MODE["RGB"]:
                return self._16_bpp_rgb()
            if view_mode == _IMAGE_MODE["GREYSCALE"]:
                return self._16_bpp_greyscale_scaled()
            if view_mode == _IMAGE_MODE["L_STRETCHED"]:
                return self._16_bpp_greyscale_normalized()

        if self.bytes_per_pixel == 4:
            if view_mode == _IMAGE_MODE["RGB"]:
                return self._24_bpp_rgb()
            if view_mode == _IMAGE_MODE["GREYSCALE"]:
                return self._24_bpp_greyscale_scaled()
            if view_mode == _IMAGE_MODE["L_STRETCHED"]:
                return self._24_bpp_greyscale_normalized()

        raise Exception("Unsupported bit depth")

    def _16_bpp_rgb(self):
        image_bytes = bytearray()
        offset = 0
        for _ in range(self.width * self.height):
            image_bytes.append(self.image[offset])
            image_bytes.append(self.image[offset + 1])
            image_bytes.append(0)
            offset += 2
        return Image.frombytes("RGB", (self.width, self.height), bytes(image_bytes))

    def _16_bpp_greyscale_scaled(self):
        image_bytes = bytearray()
        offset = 0
        for _ in range(self.width * self.height):
            value = self.image[offset] + (self.image[offset + 1] << 8)
            scaled_value = int(value * 0xFF / 0xFFFF)
            image_bytes.append(scaled_value)
            offset += 2
        return Image.frombytes("L", (self.width, self.height), bytes(image_bytes))

    def _16_bpp_greyscale_normalized(self):
        offset = 0
        min_value = 0xFFFF
        max_value = 0
        for _ in range(self.width * self.height):
            value = self.image[offset] + (self.image[offset + 1] << 8)
            if value < min_value:
                min_value = value
            if value > max_value:
                max_value = value
            offset += 2

        image_bytes = bytearray()
        if max_value == min_value:
            return Image.frombytes(
                "L",
                (self.width, self.height),
                bytes(bytearray(self.width * self.height)),
            )

        scale = 1.0 / (max_value - min_value)
        offset = 0
        for _ in range(self.width * self.height):
            value = self.image[offset] + (self.image[offset + 1] << 8)
            value -= min_value
            value *= scale
            image_bytes.append(int(value * 0xFF))
            offset += 2

        return Image.frombytes("L", (self.width, self.height), bytes(image_bytes))

    def _24_bpp_rgb(self):
        image_bytes = bytearray()
        offset = 0
        for _ in range(self.width * self.height):
            image_bytes.append(self.image[offset + 1])
            image_bytes.append(self.image[offset + 2])
            image_bytes.append(self.image[offset + 3])
            offset += 4

        return Image.frombytes("RGB", (self.width, self.height), bytes(image_bytes))

    def _24_bpp_greyscale_scaled(self):
        image_bytes = bytearray()
        offset = 0
        for _ in range(self.width * self.height):
            value = (
                self.image[offset + 1]
                + (self.image[offset + 2] << 8)
                + (self.image[offset + 3] << 16)
            )
            scaled_value = int(value * 0xFF / 0xFFFFFF)
            image_bytes.append(scaled_value)
            offset += 4
        return Image.frombytes("L", (self.width, self.height), bytes(image_bytes))

    def _24_bpp_greyscale_normalized(self):
        offset = 0
        min_value = 0xFFFFFF
        max_value = 0
        for _ in range(self.width * self.height):
            value = (
                self.image[offset + 1]
                + (self.image[offset + 2] << 8)
                + (self.image[offset + 3] << 16)
            )
            if value < min_value:
                min_value = value
            if value > max_value:
                max_value = value
            offset += 4

        if max_value == min_value:
            return Image.frombytes(
                "L",
                (self.width, self.height),
                bytes(bytearray(self.width * self.height)),
            )

        image_bytes = bytearray()
        scale = 1.0 / (max_value - min_value)
        offset = 0
        for _ in range(self.width * self.height):
            value = (
                self.image[offset + 1]
                + (self.image[offset + 2] << 8)
                + (self.image[offset + 3] << 16)
            )
            value -= min_value
            value *= scale
            image_bytes.append(int(value * 0xFF))
            offset += 4

        return Image.frombytes("L", (self.width, self.height), bytes(image_bytes))


class ImageInfoDialog(simpledialog.Dialog):
    _BPP_VALUES = ["8", "16", "24"]

    def __init__(
        self, parent, title, default_width=640, default_height=480, default_bpp=16
    ):
        self._valid = False
        self._width = default_width
        self._height = default_height
        self._bpp = str(default_bpp)
        self._bpp_variable = None
        super().__init__(parent, title)

    def body(self, master):
        tkinter.Label(master, text="Width:").grid(row=0)
        tkinter.Label(master, text="Height:").grid(row=1)
        tkinter.Label(master, text="Bits per pixel:").grid(row=2)

        vcmd = (master.register(self._int_validate), "%P")

        width_var = tkinter.StringVar(master)
        width_var.set(str(self._width))
        self.width_input = tkinter.Entry(
            master, textvariable=width_var, validate="key", validatecommand=vcmd
        )

        height_var = tkinter.StringVar(master)
        height_var.set(str(self._height))
        self.height_input = tkinter.Entry(
            master, textvariable=height_var, validate="key", validatecommand=vcmd
        )

        self._bpp_variable = tkinter.StringVar(master)
        self._bpp_variable.set(self._bpp)
        self.bpp_input = tkinter.OptionMenu(
            master, self._bpp_variable, *self._BPP_VALUES
        )

        self.width_input.grid(row=0, column=1)
        self.height_input.grid(row=1, column=1)
        self.bpp_input.grid(row=2, column=1)

        return self.width_input

    def apply(self):
        self._width = int(self.width_input.get())
        self._height = int(self.height_input.get())
        self._bpp = int(self._bpp_variable.get())
        self._valid = True

    @property
    def valid(self):
        return self._valid

    @property
    def image_format(self):
        return self._width, self._height, self._bpp

    @staticmethod
    def _int_validate(value_if_allowed):
        if not value_if_allowed:
            return True

        try:
            int(value_if_allowed)
            return True
        except ValueError:
            pass

        return False


class _App:
    def __init__(self, input_file, width, height, bpp):
        self.image = None
        self.tk_image = None

        self._default_width = width
        self._default_height = height
        self._default_bpp = bpp

        self._root = tkinter.Tk()
        self._root.option_add("*tearOff", tkinter.FALSE)
        self._root.title("Depth texture visualizer")

        menubar = tkinter.Menu(self._root)

        menu_file = tkinter.Menu(menubar)
        menubar.add_cascade(menu=menu_file, label="File")
        menu_file.add_command(label="Open...", command=self._on_open)

        menu_view = tkinter.Menu(menubar)
        menubar.add_cascade(menu=menu_view, label="View")

        self._view_mode = tkinter.StringVar(value=_IMAGE_MODE["RGB"])
        menu_view.add_radiobutton(
            label="RGB",
            variable=self._view_mode,
            value=_IMAGE_MODE["RGB"],
            command=self._on_view_mode_changed,
        )
        menu_view.add_radiobutton(
            label="Greyscale",
            variable=self._view_mode,
            value=_IMAGE_MODE["GREYSCALE"],
            command=self._on_view_mode_changed,
        )
        menu_view.add_radiobutton(
            label="Greyscale: stretched 0..1",
            variable=self._view_mode,
            value=_IMAGE_MODE["L_STRETCHED"],
            command=self._on_view_mode_changed,
        )

        menu_zoom = tkinter.Menu(menubar)
        menubar.add_cascade(menu=menu_zoom, label="Zoom")
        self._zoom = tkinter.StringVar(value="1")
        for zoom in [1, 2, 4]:
            menu_zoom.add_radiobutton(
                label=f"{zoom}00%",
                variable=self._zoom,
                value=f"{zoom}",
                command=self._on_zoom_changed,
            )

        self._root["menu"] = menubar

        self._canvas = tkinter.Canvas(
            self._root, width=width, height=height, bg="black"
        )
        self._canvas.pack()

        self._hover_value_variable = tkinter.StringVar()
        self._hover_value_label = tkinter.Label(
            self._root, textvariable=self._hover_value_variable
        )
        self._hover_value_label.pack(anchor="s")

        self._click_value_variable = tkinter.StringVar()
        self._click_value_label = tkinter.Label(
            self._root, textvariable=self._click_value_variable
        )
        self._click_value_label.pack(anchor="s")

        self._canvas.bind("<Motion>", self._on_canvas_mouse_move)
        self._canvas.bind("<Button-1>", self._on_canvas_mouse_click)

        if input_file:
            self.image = DepthImage(
                input_file, self._default_width, self._default_height, self._default_bpp
            )
            self._update_canvas()

    def run(self):
        self._root.mainloop()

    def _on_view_mode_changed(self):
        self._update_canvas()

    def _on_zoom_changed(self):
        self._update_canvas()

    def _set_hover_value(self, x, y, value):
        if value is None:
            self._hover_value_variable.set("")
            return

        max_value = (1 << self.image.bpp) - 1
        float_value = value / max_value
        self._hover_value_variable.set(
            f"Hover: {x}, {y} = {value} (0x{value:X} {float_value:.4f})"
        )

    def _set_click_value(self, x, y, value):
        if value is None:
            self._click_value_variable.set("")
            return

        max_value = (1 << self.image.bpp) - 1
        float_value = value / max_value
        self._click_value_variable.set(
            f"Click: {x}, {y} = {value} (0x{value:X} {float_value:.4f})"
        )

    def _on_open(self):
        filename = filedialog.askopenfilename(
            title="Select raw depth texture", filetypes=[("Raw dump", "*.raw")]
        )
        if not filename:
            return

        info = ImageInfoDialog(
            self._root,
            "Image info",
            self._default_width,
            self._default_height,
            self._default_bpp,
        )
        if not info.valid:
            return

        self.image = DepthImage(filename, *info.image_format)
        self._update_canvas()

    def _update_canvas(self):
        if not self.image:
            return

        zoom = float(self._zoom.get())
        w = int(self.image.width * zoom)
        h = int(self.image.height * zoom)

        pil_image = self.image.to_pil_image(self._view_mode.get())
        if zoom != 1:
            pil_image = pil_image.resize((w, h))
        self.tk_image = ImageTk.PhotoImage(pil_image)
        self._canvas.config(width=w, height=h)
        self._canvas.pack()
        self._canvas.create_image(0, 0, image=self.tk_image, anchor="nw")

    def _get_image_offset(self, event):
        zoom = float(self._zoom.get())
        x = int(event.x / zoom)
        y = int(event.y / zoom)

        return x, y

    def _on_canvas_mouse_move(self, event):
        if not self.image:
            self._set_hover_value(0, 0, None)
            return

        x, y = self._get_image_offset(event)
        self._set_hover_value(x, y, self.image.value_at(x, y))

    def _on_canvas_mouse_click(self, event):
        if not self.image:
            self._set_hover_value(0, 0, None)
            return

        x, y = self._get_image_offset(event)
        self._set_click_value(x, y, self.image.value_at(x, y))


def main(args):
    app = _App(args.input, args.width, args.height, args.bpp)
    app.run()
    return 0


if __name__ == "__main__":

    def _parse_args():
        parser = argparse.ArgumentParser()

        parser.add_argument(
            "-i",
            "--input",
            metavar="path",
            help="Open the given file directly.",
        )

        parser.add_argument(
            "--width",
            metavar="pixels",
            type=int,
            default=640,
            help="Default texture width.",
        )

        parser.add_argument(
            "--height",
            metavar="pixels",
            type=int,
            default=480,
            help="Default texture height.",
        )

        parser.add_argument(
            "-d",
            "--bpp",
            metavar="bits_per_pixel",
            type=int,
            default=16,
            help="Default bits per pixel.",
        )

        return parser.parse_args()

    sys.exit(main(_parse_args()))
