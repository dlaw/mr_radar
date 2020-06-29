#!/usr/bin/python
import argparse, jinja2, os, os.path

def generate_html(template_path, subdir):
    with open(template_path) as f:
        template = jinja2.Template(f.read())
    frames = [name[:-4] for name in sorted(os.listdir(subdir)) if
              name.startswith('20') and name.endswith('.png')]
    with open(os.path.join(subdir, 'index.html'), 'w') as f:
        f.write(template.render(frames=frames))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='generate HTML for an animated radar loop')
    parser.add_argument('--template', required=True, type=str,
                        help='jinja2 template file to use')
    parser.add_argument('--dir', required=True, type=str,
                        help='subdirectory with radar image files')
    opts = parser.parse_args()
    generate_html(opts.template, opts.dir)
