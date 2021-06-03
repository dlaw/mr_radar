#!/usr/bin/python
import argparse, datetime, jinja2, os, os.path

def generate_html(template_path, subdir):
    current_time = datetime.datetime.now(tz=datetime.timezone.utc)
    frame_names = sorted(os.listdir(os.path.join(subdir, 'radar')))
    frame_attrs = []
    for frame_name in frame_names:
        local_time = datetime.datetime.fromisoformat(
            os.path.splitext(frame_name)[0]).astimezone()
        age = current_time - local_time
        frame_attrs.append({'src': os.path.join('radar', frame_name),
                            'data-time': local_time.strftime('%H:%M'),
                            'data-time_ms': local_time.timestamp() * 1000,
        })
    with open(template_path) as f:
        template = jinja2.Template(f.read())
    with open(os.path.join(subdir, 'index.html'), 'w') as f:
        f.write(template.render(title=os.path.normpath(subdir),
                                frames=frame_attrs))

def generate_index(template_path, root_dir, subdir_names):
    with open(template_path) as f:
        template = jinja2.Template(f.read())
    with open(os.path.join(root_dir, 'index.html'), 'w') as f:
        f.write(template.render(subdirs=subdir_names))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='generate HTML for an animated radar loop')
    parser.add_argument('--template', required=True, type=str,
                        help='jinja2 template file to use')
    parser.add_argument('--dir', required=True, type=str,
                        help='subdirectory with radar image files')
    opts = parser.parse_args()
    generate_html(opts.template, opts.dir)
