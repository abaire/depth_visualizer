#!/usr/bin/env python3

import struct
import sys

_UNPACK_PATTERN = {
    1: "B",
    2: "<H",
    4: "<L"
}


def main(args):
    width = int(args[1])
    height = int(args[2])
    bpp = int(args[3])
    x = int(args[4])
    y = int(args[5])
    
    with open(args[0], "rb") as infile:
        content = infile.read()

    bytes_per_pixel = bpp >> 3
    pitch = width * bytes_per_pixel
    offset = y * pitch + x * bytes_per_pixel

    if offset < len(content):
        value = struct.unpack(_UNPACK_PATTERN[bytes_per_pixel],
                              content[offset:offset + bytes_per_pixel])[0]
        print(f"[{x},{y}] = {value} (0x{value:X})")
        return 0

    print("Invalid position, outside bounds of image.")
    return 1


if __name__ == '__main__':
    if len(sys.argv) < 7:
        print(f"Usage: {sys.argv[0]} <filename> <width> <height> <bits_per_pixel> <x> <y>")
        sys.exit(1)

    sys.exit(main(sys.argv[1:]))
    
