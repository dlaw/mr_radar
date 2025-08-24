const socket = io();

const radar_container = document.querySelector("#radar-container");
const map_container = document.querySelector("#map-container");
const time = document.querySelector("#time");
const timeline_marker = document.querySelector("#timeline-marker");
const speed_slider = document.querySelector("#speed");

map_container.style.zoom = "100%";

// maps radar image time to server path
let radar_paths = new Map();
let next_frame_timeout_id = null;
// time of current frame being displayed
let current_frame_time = null;
let current_speed = parseFloat(speed_slider.value);

function millis_from_path(path) {
    const last_slash = path.lastIndexOf("/");
    return new Date(path.substring(last_slash + 1).replace(".png", "")).getTime();
}

function sorted_map_from_paths(paths) {
    return new Map(paths.map(p => [millis_from_path(p), p]).sort((a, b) => a[0] - b[0]))
}

socket.on("radar-list", paths => {
    paths = paths.filter(p => p.includes("tbos"));

    const new_paths = sorted_map_from_paths(paths.filter(p => !radar_paths.values().toArray().includes(p)));
    const removed_paths = radar_paths.values().filter(p => !paths.includes(p));

    // make and add image elements for each new path
    // since new_paths is sorted based on timestamp, radar paths will be sorted
    for (const [millis_since_epoch, path] of new_paths.entries()) {
        // add image to radar container
        const img = document.createElement("img");
        img.src = path;
        img.style.opacity = "0";
        img.style.transitionDuration = transition_duration;
        img.classList.add("animated")

        radar_container.appendChild(img);
        radar_paths.set(millis_since_epoch, path);
    }

    // remove images with paths that were removed from the server
    for (const path of removed_paths) {
        const millis_since_epoch = millis_from_path(path);

        // if we're currently displaying a removed path, go to the next frame immediately
        if (current_frame_time === millis_since_epoch)
            next_frame_immediate();

        radar_container.removeChild(document.querySelector(`img[src="${path}"]`));
        radar_paths.delete(millis_since_epoch);
    }

    // start display loop if not started already
    if (next_frame_timeout_id === null) {
        current_frame_time = radar_paths.keys().next().value;
        next_frame();
    }
});

function next_frame_immediate() {
    clearTimeout(next_frame_timeout_id);
    next_frame();
}

speed_slider.oninput = () => {
    const next_speed = parseFloat(speed_slider.value)
    if (next_speed < 500)
        next_frame_immediate();

    current_speed = next_speed;
    adjust_animation_speeds();
}

function adjust_animation_speeds() {
    transition_duration = `${200 / current_speed}s`;
    for (const elem of document.querySelectorAll(".animated")) {
        elem.style.transitionDuration = transition_duration;
    }
}

function next_frame() {
    if (radar_paths.size === 0)
        return;

    const times = radar_paths.keys().toArray();
    const current_index = times.indexOf(current_frame_time);
    const next_index = (current_index + 1) % times.length;
    const next_next_index = (next_index + 1) % times.length;

    const next_frame_time = times[next_index];
    const next_next_frame_time = times[next_next_index];

    const current_img = document.querySelector(`img[src="${radar_paths.get(current_frame_time)}"]`)
    const next_img = document.querySelector(`img[src="${radar_paths.get(next_frame_time)}"]`)

    current_img.style.opacity = "0";
    next_img.style.opacity = "1.0";

    current_frame_time = next_frame_time;

    time.innerHTML = `${Math.round((Date.now() - current_frame_time) / (60 * 1000))} min ago`;
    timeline_marker.style.left = `${100 * (current_frame_time - times[0]) / (times[times.length - 1] - times[0])}%`;

    let delta = next_next_frame_time - next_frame_time;

    if (delta <= 0)
        delta = 5 * 60 * 1000;

    next_frame_timeout_id = setTimeout(next_frame, delta / current_speed);
}

// scroll to zoom stuff
let current_zoom_input = 0;
let current_zoom_actual = 0;
window.onwheel = e => {
    current_zoom_input += e.wheelDelta / 1000;
    current_zoom_actual = 100 * Math.exp(current_zoom_input);
    map_container.style.zoom = `${current_zoom_actual}%`;
}

adjust_animation_speeds();