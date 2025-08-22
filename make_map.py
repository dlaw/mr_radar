#!/usr/bin/python
import argparse, math, os.path, urllib.request
import PIL.Image, PIL.PngImagePlugin

def longitude_to_x(lon):
    return (lon + 180) / 360.
def x_to_longitude(x):
    return 360 * x - 180
def latitude_to_y(lat):
    return (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2
def y_to_latitude(y):
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y))))

def tiles(xmin, xmax, ymin, ymax, zoom):
    n = 1 << zoom
    for x in range(math.floor(xmin * n), math.ceil(xmax * n)):
        for y in range(math.floor(ymin * n), math.ceil(ymax * n)):
            yield x, y

def make_map(output_path, lat_min, lat_max, lon_min, lon_max, zoom, url):
    x_min = longitude_to_x(lon_min)
    x_max = longitude_to_x(lon_max)
    y_min = latitude_to_y(lat_max)
    y_max = latitude_to_y(lat_min)
    assert 0 <= x_min < x_max <= 1
    assert 0 <= y_min < y_max <= 1
    out_image = None
    for tile_x, tile_y in tiles(x_min, x_max, y_min, y_max, zoom):
        # Fetch the tile
        tile_url = url.format(x=tile_x, y=tile_y, z=zoom)
        try:
            tile = PIL.Image.open(urllib.request.urlopen(tile_url))
        except urllib.request.HTTPError as exc:
            raise RuntimeError(f'HTTPError trying to download from {tile_url}: Make sure API key is correctly set in config.ini!') from exc
        # If this is the first tile, create the output image
        if not out_image:
            pixels_per_tile = tile.size[0]
            pixels_per_world = pixels_per_tile * (1 << zoom)
            pix_x_min = math.floor(x_min * pixels_per_world)
            pix_x_max = math.ceil(x_max * pixels_per_world)
            pix_y_min = math.floor(y_min * pixels_per_world)
            pix_y_max = math.ceil(y_max * pixels_per_world)
            out_size = (pix_x_max - pix_x_min, pix_y_max - pix_y_min)
            out_image = PIL.Image.new('RGBA', out_size, (0, 0, 255, 0))
        assert tile.size[0] == tile.size[1] == pixels_per_tile
        x_origin = tile_x * pixels_per_tile - pix_x_min
        y_origin = tile_y * pixels_per_tile - pix_y_min
        out_image.paste(tile, box=(x_origin, y_origin))
    # Add the latitude and longitude extents as PNG metadata
    metadata = PIL.PngImagePlugin.PngInfo()
    metadata.add_text("Minimum Latitude", '{:.6f}'.format(
        y_to_latitude(pix_y_max / pixels_per_world)))
    metadata.add_text("Maximum Latitude", '{:.6f}'.format(
        y_to_latitude(pix_y_min / pixels_per_world)))
    metadata.add_text("Minimum Longitude", '{:.6f}'.format(
        x_to_longitude(pix_x_min / pixels_per_world)))
    metadata.add_text("Maximum Longitude", '{:.6f}'.format(
        x_to_longitude(pix_x_max / pixels_per_world)))
    out_image.save(output_path, pnginfo=metadata)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='assemble a map from tiles')
    parser.add_argument('--out', required=True, type=str,
                        help='path to output png image file')
    parser.add_argument('--lat_min', required=True, type=float,
                        help='minimum latitude of output image')
    parser.add_argument('--lat_max', required=True, type=float,
                        help='maximum latitude of output image')
    parser.add_argument('--lon_min', required=True, type=float,
                        help='minimum longitude of output image')
    parser.add_argument('--lon_max', required=True, type=float,
                        help='maximum longitude of output image')
    parser.add_argument('--zoom', required=True, type=int,
                        help='zoom level of tiles to download')
    parser.add_argument('--url', required=True, type=str,
                        help='tile URL with {x}/{y}/{z} for substitution')
    opts = parser.parse_args()
    make_map(opts.out, opts.lat_min, opts.lat_max, opts.lon_min,
             opts.lon_max, opts.zoom, opts.url)
