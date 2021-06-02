#!/usr/bin/python
import argparse, configparser, datetime, os, os.path, time, urllib.request
import PIL.Image, PIL.PngImagePlugin
import level3_to_png, make_map, generate_html

# MetPy (plots/__init__.py) outputs a warning about Cartopy not being
# installed unless we do a little song and dance with the logging
import logging
logging.disable(logging.ERROR)
import metpy.io
logging.disable(logging.NOTSET)

parser = argparse.ArgumentParser(
    description='weather radar visualization tool')
parser.add_argument('--config', required=False, type=str,
                    help='path to config file', default='config.ini')
parser.add_argument('--repeat', required=False, type=int, default=0,
                    help='number of seconds to automatically repeat')
opts = parser.parse_args()

config = configparser.ConfigParser()
config.read(opts.config)

def radar_update(radar_layer, settings):
    out_dir = settings['out_dir']

    radar_dir = os.path.join(out_dir, radar_layer)
    if not os.path.exists(radar_dir):
        os.makedirs(radar_dir)

    # Generate the map images if they don't already exist
    # TODO: identify if/when the map parameters change
    for map_type in ['base_map', 'overlay_map']:
        map_path = os.path.join(radar_dir, '{}.png'.format(map_type))
        # Create the map if it doesn't already exist.
        if not os.path.exists(map_path):
            make_map.make_map(map_path,
                              settings.getfloat('latitude_min'),
                              settings.getfloat('latitude_max'),
                              settings.getfloat('longitude_min'),
                              settings.getfloat('longitude_max'),
                              settings.getint('zoom'),
                              settings[map_type])

    # Make sure the maps that we have are the same size
    base_image = PIL.Image.open(os.path.join(radar_dir, 'base_map.png'))
    overlay_image = PIL.Image.open(os.path.join(radar_dir, 'overlay_map.png'))
    assert base_image.size == overlay_image.size
    x_res, y_res = base_image.size

    # Render radar data using latitude and longitude from the map image
    # metadata, instead of from the configuration file, because the image
    # extents may be slightly different (due to rounding to the nearest
    # pixel edge).
    lat_min = float(base_image.info['Minimum Latitude'])
    lat_max = float(base_image.info['Maximum Latitude'])
    lon_min = float(base_image.info['Minimum Longitude'])
    lon_max = float(base_image.info['Maximum Longitude'])
    try:
        response = urllib.request.urlopen(settings['radar_url'])
    except ConnectionResetError:
        print('Error downloading {}'.format(settings['radar_url']))
        return
    radar_file = metpy.io.Level3File(response)
    # TODO: also save radar_file if desired
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
    # TODO: warn if prod_time is too old.
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
    generate_html.generate_html('radar_template.html',
                                os.path.join(out_dir, radar_layer))

try:
    while True:
        for radar_layer in config.sections():
            radar_update(radar_layer, config[radar_layer])
        if opts.repeat == 0:
            exit()
        print('Update: {}'.format(datetime.datetime.now()
                                  .isoformat(' ', 'minutes')))
        time.sleep(opts.repeat)
except KeyboardInterrupt:
    pass
