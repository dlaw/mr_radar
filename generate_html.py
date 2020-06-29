#!/usr/bin/python
import argparse, datetime, jinja2, os, os.path

def generate_html(template_path, subdir):
    with open(template_path) as f:
        template = jinja2.Template(f.read())
    frames = []
    current_time = datetime.datetime.now(tz=datetime.timezone.utc)
    for frame in sorted(os.listdir(os.path.join(subdir, 'radar'))):
        local_time = datetime.datetime.fromisoformat(
            os.path.splitext(frame)[0]).astimezone()
        age = current_time - local_time
        frames.append({'src': os.path.join('radar', frame),
                       'data-time': local_time.strftime('%H:%M'),
                       'data-age': int(age.total_seconds())
        })
    with open(os.path.join(subdir, 'index.html'), 'w') as f:
        f.write(template.render(title=os.path.normpath(subdir),
                                frames=frames))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='generate HTML for an animated radar loop')
    parser.add_argument('--template', required=True, type=str,
                        help='jinja2 template file to use')
    parser.add_argument('--dir', required=True, type=str,
                        help='subdirectory with radar image files')
    opts = parser.parse_args()
    generate_html(opts.template, opts.dir)
