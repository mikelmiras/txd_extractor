import os
import random
from PIL import Image
import io
import numpy as np
import cv2


def parseXBytes(data:bytes, start:int, byte_count:int, raw:bool=False) -> list[int]:
    if not raw:
        n = int.from_bytes(data[start:byte_count + start], "little")
    else:
        n = data[start:byte_count + start]
    
    start += byte_count
    return n, start


def decode_texture_to_image(texture_data):
    # Extract image properties
    width = texture_data['width']
    height = texture_data['height']
    depth = texture_data['depth']
    palette = texture_data.get('palette')
    data = texture_data['data']
    name = texture_data["name"]
    print(name)
    # If it's an 8-bit image, use a palette
    if depth == 8 and palette:
        # The palette is stored in 256 * 4 (RGBA format), convert it to a form Pillow can use
        palette_bytes = bytes(palette)  # Assuming palette is in RGBA format

        # Create an 8-bit image using the palette
        img = Image.frombytes('P', (width, height), bytes(data))  # 'P' means palette-based image
        img.putpalette(palette_bytes[:256 * 3])  # Pillow needs an RGB palette (not RGBA)
    
    # If it's a 24-bit or 32-bit image, treat it as RGB or RGBA
    elif depth == 24:
        img = Image.frombytes('RGB', (width, height), bytes(data))
    elif depth == 32:
        img = Image.frombytes('RGBA', (width, height), bytes(data))
    else:
        raise ValueError(f"Unsupported depth: {depth}")

    # Optionally save or show the image
    img.save("textures/{}.png".format(str(random.randint(9, 99999))), "png")

    return img

def parseMipMaps(data:bytes, start:int, mipmap_count:int) -> list[int]:
    mipmap_bin = b''
    for i in range(0, mipmap_count - 1):
        data_size, start = parseXBytes(data, start, 4)
        mipmap_bin += data[start:start + data_size]
        start += data_size
    return mipmap_bin, start

textures = []
count = 0

def decode_4bit_grayscale_texture(texture_data):
    width = texture_data['width']
    height = texture_data['height']
    data = texture_data['data']  # Packed 4-bit pixel data
    
    # Create a blank numpy array to store the unpacked 8-bit pixel data
    pixel_data = np.zeros((height, width), dtype=np.uint8)

    # Unpack 4-bit pixels (two pixels per byte)
    for y in range(height):
        for x in range(0, width, 2):
            byte = data[(y * width // 2) + (x // 2)]
            # High nibble (first pixel)
            high_pixel = (byte >> 4) & 0x0F
            # Low nibble (second pixel)
            low_pixel = byte & 0x0F
            
            # Map 4-bit values to 8-bit grayscale (0–255)
            pixel_data[y, x] = int((high_pixel / 15) * 255)  # High nibble pixel
            if x + 1 < width:
                pixel_data[y, x + 1] = int((low_pixel / 15) * 255)  # Low nibble pixel

    # Create a grayscale Pillow image
    img = Image.fromarray(pixel_data, mode='L')  # 'L' mode is for grayscale images

    # Show or save the image
    img.show()

    return img

def dataParser(data:bytes):
    global textures
    global count
    i = 0
    iterations = 0
    byte_count = len(data)
    inside_texture = False
    while (i < byte_count):
        iterations += 1
        theid, i = parseXBytes(data, i, 4)
        chunk_size, i = parseXBytes(data, i, 4)
        rw_version, i = parseXBytes(data, i, 4)
        print(theid)
        if (theid == 22):
            print("txd_file_t found")
        elif (theid == 1 and not inside_texture):
            print("txd_info_t found")
            count = int.from_bytes(data[i:i+2], "little")
            i += 2
            print("Count: ", count)
            i += 2
        elif (theid == 1 and inside_texture):
            version, i = parseXBytes(data, i, 4)
            filter_flags, i = parseXBytes(data, i, 4)
            texture_name, i = parseXBytes(data, i, 32, True)
            alpha_name, i = parseXBytes(data, i, 32, True)
            alpha_flags, i = parseXBytes(data, i, 4)
            direct3d_texture_format, i = parseXBytes(data, i, 4, True)
            width, i = parseXBytes(data, i, 2)
            height, i = parseXBytes(data, i, 2)
            depth, i = parseXBytes(data, i, 1)
            mipmap_count, i = parseXBytes(data, i, 1)
            texcode_type, i = parseXBytes(data, i, 1)
            flags, i = parseXBytes(data, i, 1)
            palette = None
            if (depth == 9):
                print("Palette found")
                palette, i = parseXBytes(data, i, 1024)
            data_size, i = parseXBytes(data, i, 4)
            name = texture_name.replace(b"\x00", b"")
            textures.append(name)
            d, i = parseXBytes(data, i, data_size, True)

            ob = {"name":texture_name.decode(), "direct3d_texture_format":direct3d_texture_format, "width":width, "height":height, "depth":depth, "mipmap_count":mipmap_count, "data_size":data_size, "data_real_size":len(d)}
            mipmaps, i = parseMipMaps(data, i, mipmap_count)
            print(ob)
            ob["data"] = d
            
            decode_texture_to_image(ob)
            f2 = open("textures/{}".format(name.decode()), "w+b")
            f2.write(d)
            f2.close()
            inside_texture = False
           
            
        elif (theid == 21):
            print("txd_texture_t found, next chunk should be txd_texture_data_t")
            inside_texture = True
        elif (theid == 3):
            print("txd_extra_info_t found")
        else:
            print("Unknown chunk found: ", theid)
            break
            

        # print("%{} proccessed".format(str(int( (i/byte_count) * 100 ))))

    
        

def readChunk(data:bytes) -> list[int]:
    theid =  int.from_bytes(data[:4], 'little')
    chunk_size = int.from_bytes(data[4:8], "little")
    rw_version = int.from_bytes(data[8:12], "little")
    if (theid == 1):
        count = int.from_bytes(data[12:14], "little")
        print("Texture count: ", count)
        print("Chunk size: ", chunk_size)
    return theid, chunk_size, rw_version

f = open("vincent.txd", "rb")
data = f.read()
# theid, chunk_size, rw_version = readChunk(data)

# raw_rw_version = data[8:12]
# data = data[12:]
# next_chunk = readChunk(data)
# i = 0
f.close()

dataParser(data)

print("Found textures: ", len(textures), ". There should be: ", count)
print([t.decode("ascii") for t in textures])
