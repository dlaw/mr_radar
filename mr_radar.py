#!/usr/bin/python
import argparse, configparser, os, os.path, urllib.request
import metpy.io
import PIL.Image, PIL.PngImagePlugin
import level3_to_png, make_map, generate_html

parser = argparse.ArgumentParser(
    description='weather radar visualization tool')
parser.add_argument('--config', required=False, type=str,
                    help='path to config file', default='config.ini')
opts = parser.parse_args()

config = configparser.ConfigParser()
config.read(opts.config)

for section in config.sections():
    if not os.path.exists(section):
        os.mkdir(section)
    map_path = section + '/map.png'
    if not os.path.exists(map_path):
        make_map.make_map(map_path,
            config.getfloat(section, 'latitude_min'),
            config.getfloat(section, 'latitude_max'),
            config.getfloat(section, 'longitude_min'),
            config.getfloat(section, 'longitude_max'),
            config.getint(section, 'map_zoom'),
            config.get(section, 'map_url'))
    map_image = PIL.Image.open(map_path)
    x_res, y_res = map_image.size
    lat_min = float(map_image.info['Minimum Latitude'])
    lat_max = float(map_image.info['Maximum Latitude'])
    lon_min = float(map_image.info['Minimum Longitude'])
    lon_max = float(map_image.info['Maximum Longitude'])
    response = urllib.request.urlopen(config.get(section, 'radar_url'))
    radar_file = metpy.io.Level3File(response)
    radar_image = level3_to_png.level3_to_png(
        radar_file, lat_min, lat_max, lon_min, lon_max, x_res, y_res)
    assert map_image.size == radar_image.size
    radar_image.paste(map_image, mask=map_image)
    prod_time = radar_file.metadata['prod_time'].strftime('%Y-%m-%d_%H:%M')
    metadata = PIL.PngImagePlugin.PngInfo()
    for label in ["Minimum Latitude", "Maximum Latitude",
                  "Minimum Longitude", "Maximum Longitude"]:
        metadata.add_text(label, map_image.info[label])
    radar_image.save('{}/{}.png'.format(section, prod_time),
                     pnginfo=metadata)
    generate_html.generate_html('template.html', section)
