import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, send_file, abort
from flask_socketio import SocketIO, emit

from glob import glob
from pathlib import Path

from mr_radar import config, radar_update


app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

def radar_update_thread():
    while True:
        for radar_layer in config.sections():
            radar_update(radar_layer, config[radar_layer])

        socketio.emit('radar-list', get_radar_image_paths(), namespace='/')
        socketio.sleep(60)

def get_radar_image_paths():
    return glob('data/*/radar/*.png')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data/<path:filename>')
def radar_image(filename):
    full_path = Path('data') / filename

    if full_path.exists():
        return send_file(full_path)
    else:
        abort(404)

@socketio.on('connect')
def connect():
    emit('radar-list', get_radar_image_paths())

if __name__ == '__main__':
    socketio.start_background_task(radar_update_thread)
    socketio.run(app, debug=True)