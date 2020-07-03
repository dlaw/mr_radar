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

out_dir = config['general']['out_dir']

for map_type in ['base', 'overlay']:
    map_path = os.path.join(out_dir, '{}_map.png'.format(map_type))
    # Create the map if it doesn't already exist.
    if not os.path.exists(map_path):
        make_map.make_map(map_path,
                          config.getfloat('extents', 'latitude_min'),
                          config.getfloat('extents', 'latitude_max'),
                          config.getfloat('extents', 'longitude_min'),
                          config.getfloat('extents', 'longitude_max'),
                          config.getint('map_layers', 'zoom'),
                          config['map_layers'][map_type])
base_image = PIL.Image.open(os.path.join(out_dir, 'base_map.png'))
overlay_image = PIL.Image.open(os.path.join(out_dir, 'overlay_map.png'))
assert base_image.size == overlay_image.size
x_res, y_res = base_image.size

def radar_update(radar_layer, radar_url):
    radar_dir = os.path.join(out_dir, radar_layer)
    if not os.path.exists(radar_dir):
        os.mkdir(radar_dir)
    # Render radar data using latitude and longitude from the map image
    # metadata, instead of from the configuration file, because the image
    # extents may be slightly different (due to rounding to the nearest
    # pixel edge).
    lat_min = float(base_image.info['Minimum Latitude'])
    lat_max = float(base_image.info['Maximum Latitude'])
    lon_min = float(base_image.info['Minimum Longitude'])
    lon_max = float(base_image.info['Maximum Longitude'])
    try:
        response = urllib.request.urlopen(radar_url)
    except ConnectionResetError:
        print('Error downloading {}'.format(radar_url))
    radar_file = metpy.io.Level3File(response)
    # TODO: also save radar_file
    radar_image = level3_to_png.level3_to_png(
        radar_file, lat_min, lat_max, lon_min, lon_max, x_res, y_res)
    assert base_image.size == radar_image.size
    metadata = PIL.PngImagePlugin.PngInfo()
    for label in ["Minimum Latitude", "Maximum Latitude",
                  "Minimum Longitude", "Maximum Longitude"]:
        metadata.add_text(label, base_image.info[label])
    # Save the output file.
    radar_subdir = os.path.join(radar_dir, 'radar')
    if not os.path.exists(radar_subdir):
        os.mkdir(radar_subdir)
    prod_time = (radar_file.metadata['prod_time']
                 .replace(tzinfo=datetime.timezone.utc)
                 .isoformat(timespec='seconds'))
    radar_path = os.path.join(radar_subdir, '{}.png'.format(prod_time))
    radar_image.save(radar_path, pnginfo=metadata)
    # Remove stale images from the output directory.
    for radar_name in os.listdir(radar_subdir):
        prod_time = os.path.splitext(radar_name)[0]
        then = datetime.datetime.fromisoformat(prod_time)
        now = datetime.datetime.now(tz=datetime.timezone.utc)
        if now - then > datetime.timedelta(hours=1):
            os.unlink(os.path.join(radar_subdir, radar_name))
    # Regenerate the HTML template.
    generate_html.generate_html('template.html',
                                os.path.join(out_dir, radar_layer))

try:
    while True:
        for radar_layer, radar_url in config['radar_layers'].items():
            radar_update(radar_layer, radar_url)
        if opts.repeat == 0:
            exit()
        print('Update: {}'.format(datetime.datetime.now()
                                  .isoformat(' ', 'minutes')))
        time.sleep(opts.repeat)
except KeyboardInterrupt:
    pass
