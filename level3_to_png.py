#!/usr/bin/python
import argparse, io, numpy, pyproj, sys
import metpy.io, metpy.plots
import matplotlib
import PIL.Image
matplotlib.use('Agg')

def level3_to_png(radar_file, lat_min, lat_max, lon_min, lon_max,
                  x_res, y_res, min_signal_dBZ=0):
    # Open radar file and extract the data array.
    f = (radar_file if type(radar_file) == metpy.io.Level3File else
         metpy.io.Level3File(radar_file))
    data = f.map_data(f.sym_block[0][0]['data'])  # data is now in dBZ
    with numpy.errstate(invalid='ignore'):  # ignore existing NaNs
        data[data < min_signal_dBZ] = numpy.nan  # mask out low values

    # Compute the azimuth and distance at the *corners* of each sample.
    # azimuth is in degrees and distance is in meters.
    azimuth = numpy.concatenate([f.sym_block[0][0]['start_az'],
                                 [f.sym_block[0][0]['end_az'][-1]]])
    distance = numpy.linspace(0, f.max_range * 1000, data.shape[-1] + 1)

    # Project to EPSG3857 (i.e. "Web Mercator") X and Y coordinates.
    lon, lat, _ = pyproj.Geod(ellps='WGS84').fwd(
        *numpy.broadcast_arrays(f.lon, f.lat, azimuth[:,None], distance))
    radar_x, radar_y = pyproj.Proj(3857)(lon, lat)

    # Project and verify the bounds for the output image.
    xmin, ymin = pyproj.Proj(3857)(lon_min, lat_min)
    xmax, ymax = pyproj.Proj(3857)(lon_max, lat_max)
    assert abs(y_res * (xmax - xmin) / (ymax - ymin) - x_res) < 1
    assert abs(x_res * (ymax - ymin) / (xmax - xmin) - y_res) < 1

    # Generate the output plot.
    import matplotlib.pyplot
    fig = matplotlib.pyplot.figure(frameon=False, dpi=256,
                                   figsize=(x_res / 256., y_res / 256.))
    ax = matplotlib.pyplot.Axes(fig, [0, 0, 1, 1],
                                xlim=(xmin, xmax), ylim=(ymin, ymax))
    ax.set_axis_off()
    fig.add_axes(ax)
    # MetPy color table starts from -20 dB in 0.5 dB increments
    norm, cmap = metpy.plots.colortables.get_with_steps(
        'NWSStormClearReflectivity', -20, 0.5)
    ax.pcolormesh(radar_x, radar_y, data, norm=norm, cmap=cmap)

    # Export a PNG from matplotlib and pipe it into PIL.
    png_buffer = io.BytesIO()
    matplotlib.pyplot.savefig(png_buffer, format='png')
    matplotlib.pyplot.close()
    png_buffer.seek(0)
    return PIL.Image.open(png_buffer)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='convert level 3 radar file to png image')
    parser.add_argument('--radar', required=True, type=str,
                        help='path to input radar data file')
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
    parser.add_argument('--x_res', required=True, type=int,
                        help='horizontal resolution of output image')
    parser.add_argument('--y_res', required=True, type=int,
                        help='vertical resolution of output image')
    opts = parser.parse_args()
    image = level3_to_png(opts.radar, opts.lat_min, opts.lat_max,
                          opts.lon_min, opts.lon_max,
                          opts.x_res, opts.y_res)
    image.save(opts.out)
