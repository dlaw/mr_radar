#!/usr/bin/python
import argparse, configparser, datetime, os, os.path, time, urllib.request
import metpy.io
import PIL.Image, PIL.PngImagePlugin
import level3_to_png, make_map, generate_html

parser = argparse.ArgumentParser(
    description='weather radar visualization tool')
parser.add_argument('--config', required=False, type=str,
                    help='path to config file', default='config.ini')
parser.add_argument('--repeat', required=False, type=int, default=0,
                    help='number of seconds to automatically repeat')
opts = parser.parse_args()

config = configparser.ConfigParser()
config.read(opts.config)

def radar_update(section):
    if not os.path.exists(section):
        os.mkdir(section)
    map_path = section + '/map.png'
    # Create the map if it doesn't already exist
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
    # Render radar data using latitude and longitude from the map image
    # metadata, instead of from the configuration file, because the image
    # extents may be slightly different (due to rounding to the nearest
    # pixel edge).
    lat_min = float(map_image.info['Minimum Latitude'])
    lat_max = float(map_image.info['Maximum Latitude'])
    lon_min = float(map_image.info['Minimum Longitude'])
    lon_max = float(map_image.info['Maximum Longitude'])
    response = urllib.request.urlopen(config.get(section, 'radar_url'))
    radar_file = metpy.io.Level3File(response)
    radar_image = level3_to_png.level3_to_png(
        radar_file, lat_min, lat_max, lon_min, lon_max, x_res, y_res)
    # Layer the (mostly-transparent) map image atop the radar image.
    assert map_image.size == radar_image.size
    radar_image.paste(map_image, mask=map_image)
    # Add latitude and longitude extents to radar image metadata.
    # TODO: transfer additional metadata from the input radar file.
    metadata = PIL.PngImagePlugin.PngInfo()
    for label in ["Minimum Latitude", "Maximum Latitude",
                  "Minimum Longitude", "Maximum Longitude"]:
        metadata.add_text(label, map_image.info[label])
    # Save the output file.
    radar_dir = os.path.join(section, 'radar')
    if not os.path.exists(radar_dir):
        os.mkdir(radar_dir)
    prod_time = (radar_file.metadata['prod_time']
                 .replace(tzinfo=datetime.timezone.utc)
                 .isoformat(timespec='seconds'))
    radar_path = os.path.join(radar_dir, '{}.png'.format(prod_time))
    radar_image.save(radar_path, pnginfo=metadata)
    # Remove stale images from the output directory.
    for radar_name in os.listdir(radar_dir):
        prod_time = os.path.splitext(radar_name)[0]
        then = datetime.datetime.fromisoformat(prod_time)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        if now - then > datetime.timedelta(hours=1):
            os.unlink(os.path.join(radar_dir, radar_name))
    # Regenerate the HTML template.
    generate_html.generate_html('template.html', section)

try:
    while True:
        for section in config.sections():
            radar_update(section)
        if opts.repeat == 0:
            exit()
        print('Update: {}'.format(datetime.datetime.now().isoformat()))
        time.sleep(opts.repeat)
except KeyboardInterrupt:
    pass
