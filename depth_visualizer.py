#!/usr/bin/env python3

import struct
import sys
import tkinter
from tkinter import filedialog
from tkinter import simpledialog

from PIL import Image
from PIL import ImageTk

_UNPACK_PATTERN = {
    1: "B",
    2: "<H",
    4: "<L"
}

class DepthImage:
    def __init__(self, filename, width, height, bpp):
        self.width = width
        self.height = height
        self.bpp = bpp
        self.bytes_per_pixel = bpp >> 3
        self.pitch = width * self.bytes_per_pixel

        with open(filename, "rb") as infile:
            self.image = infile.read()

    def value_at(self, x, y):
        offset = y * self.pitch + x * self.bytes_per_pixel
        value = struct.unpack(_UNPACK_PATTERN[self.bytes_per_pixel],
                              self.image[offset:offset + self.bytes_per_pixel])[0]
        return value

    def to_pil_image(self):
        if self.bytes_per_pixel == 1:
            return Image.frombytes("L", (self.width, self.height), self.image)

        if self.bytes_per_pixel == 2:
            image_bytes = bytearray()
            offset = 0
            for _ in range(self.width * self.height):
                image_bytes.append(self.image[offset])
                image_bytes.append(self.image[offset + 1])
                image_bytes.append(0)
                offset += 2
            return Image.frombytes("RGB", (self.width, self.height), bytes(image_bytes))

        if self.bytes_per_pixel == 4:
            image_bytes = bytearray()
            offset = 0
            for _ in range(self.width * self.height):
                image_bytes.append(self.image[offset])
                image_bytes.append(self.image[offset + 1])
                image_bytes.append(self.image[offset + 2])
                offset += 4

            return Image.frombytes("RGB", (self.width, self.height), bytes(image_bytes))

        raise Exception("Unsupported bit depth")

class ImageInfoDialog(simpledialog.Dialog):
    _BPP_VALUES = ["8", "16", "24"]

    def __init__(self, parent, title, default_width=640, default_height=480):
        self._valid = False
        self._width = default_width
        self._height = default_height
        self._bpp = self._BPP_VALUES[1]
        self._bpp_variable = None
        super().__init__(parent, title)

    def body(self, master):
        tkinter.Label(master, text="Width:").grid(row=0)
        tkinter.Label(master, text="Height:").grid(row=1)
        tkinter.Label(master, text="Bits per pixel:").grid(row=2)

        vcmd = (master.register(self._int_validate), '%P')

        width_var = tkinter.StringVar(master)
        width_var.set(str(self._width))
        self.width_input = tkinter.Entry(master, textvariable=width_var, validate="key", validatecommand=vcmd)

        height_var = tkinter.StringVar(master)
        height_var.set(str(self._height))
        self.height_input = tkinter.Entry(master, textvariable=height_var, validate="key", validatecommand=vcmd)

        self._bpp_variable = tkinter.StringVar(master)
        self._bpp_variable.set(self._bpp)
        self.bpp_input = tkinter.OptionMenu(master, self._bpp_variable, *self._BPP_VALUES)

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
    def __init__(self):
        self.image = None

        self._root = tkinter.Tk()
        self._root.option_add('*tearOff', tkinter.FALSE)
        windowing_system = self._root.tk.call('tk', 'windowingsystem')
        self._root.title("Depth texture visualizer")

        menubar = tkinter.Menu(self._root)
        menu_file = tkinter.Menu(menubar)
        menubar.add_cascade(menu=menu_file, label="File")
        menu_file.add_command(label="Open...",  command=self._on_open)
        self._root['menu'] = menubar

        self._canvas = tkinter.Canvas(self._root, width=640, height=480, bg="black")
        self._canvas.pack()

        self._hover_value_variable = tkinter.StringVar()
        self._hover_value_label = tkinter.Label(self._root, textvariable=self._hover_value_variable)
        self._hover_value_label.pack(anchor="s")

        self._click_value_variable = tkinter.StringVar()
        self._click_value_label = tkinter.Label(self._root, textvariable=self._click_value_variable)
        self._click_value_label.pack(anchor="s")

        self._canvas.bind('<Motion>', self._on_canvas_mouse_move)
        self._canvas.bind('<Button-1>', self._on_canvas_mouse_click)

    def run(self):
        self._root.mainloop()

    def _set_hover_value(self, x, y, value):
        if value is None:
            self._hover_value_variable.set("")
            return

        self._hover_value_variable.set(f"Hover: {x}, {y} = {value} (0x{value:X})")

    def _set_click_value(self, x, y, value):
        if value is None:
            self._click_value_variable.set("")
            return

        self._click_value_variable.set(f"Click: {x}, {y} = {value} (0x{value:X})")

    def _on_open(self):
        filename = filedialog.askopenfilename(
            title="Select raw depth texture", filetypes=[("Raw dump", "*.raw")])
        if not filename:
            return

        info = ImageInfoDialog(self._root, "Image info")
        if not info.valid:
            return

        self.image = DepthImage(filename, *info.image_format)
        self.tk_image = ImageTk.PhotoImage(self.image.to_pil_image())
        self._canvas.config(width=self.image.width, height=self.image.height)
        self._canvas.pack()
        self._canvas.create_image(0, 0, image=self.tk_image, anchor="nw")

    def _on_canvas_mouse_move(self, event):
        if not self.image:
            self._set_hover_value(0, 0, None)
            return

        self._set_hover_value(event.x, event.y, self.image.value_at(event.x, event.y))

    def _on_canvas_mouse_click(self, event):
        if not self.image:
            self._set_hover_value(0, 0, None)
            return

        self._set_click_value(event.x, event.y, self.image.value_at(event.x, event.y))


def main():
    app = _App()
    app.run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
    
