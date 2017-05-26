#!/usr/bin/env python3
"""Install pygtk, pycairo, gobject in a virtualenv at argv[1]"""


import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import requests


try:
    VENV = sys.argv[1]
except IndexError:
    VENV = './venv'
VENV_PY = os.path.join(VENV, 'bin', 'python')
CAIRO = {
    'name': 'cairo',
    'src': 'http://cairographics.org/releases/py2cairo-1.10.0.tar.bz2',
    'config': ['./waf', 'configure', '--prefix=' + os.path.abspath(VENV)],
    'build': ['./waf', 'build'],
    'install': ['./waf', 'install']
}
GOBJECT = {
    'name': 'gobject',
    'src': 'http://ftp.gnome.org/pub/GNOME/sources/pygobject/2.28/pygobject-2.28.6.tar.bz2',
    'config': [
        './configure', '--prefix=' + os.path.abspath(VENV),
        '--disable-introspection',
    ],
    'build': ['make'],
    'install': ['make', 'install']
}
LIBGLADE = {
    'name': 'gtk.glade',
    'src': 'http://ftp.gnome.org/pub/GNOME/sources/libglade/2.6/libglade-2.6.4.tar.bz2',
    'config': ['./configure', '--prefix=' + os.path.abspath(VENV)],
    'build': ['make'],
    'install': ['make', 'install']
}
GTK = {
    'name': 'gtk',
    'src': 'https://pypi.python.org/packages/source/P/PyGTK/pygtk-2.24.0.tar.bz2',
    'config': [
        './configure', '--prefix=' + os.path.abspath(VENV),
        'PKG_CONFIG_PATH=' + os.path.join(os.path.abspath(VENV), 'lib', 'pkgconfig')
    ],
    'build': ['make'],
    'install': ['make', 'install']
}
IMPORT_TEST = \
"""
try:
    import {0}
except ImportError:
    raise SystemExit(-1)
"""


def download_and_unpack(pkg, tempdir):
    """Download src to tempdir and extract it"""
    r = requests.get(pkg.get('src'), stream=True)
    dest = os.path.join(tempdir, pkg.get('src').rsplit('/', 1)[-1])
    with open(dest, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk: # filter out keepalives
                f.write(chunk)
    tarobj = tarfile.open(dest)
    try:
        tarobj.extractall(path=tempdir)
    finally:
        tarobj.close()


def test_import(pkg, interpreter):
    """Test an import using the given python interpreter"""
    res = subprocess.call(
        [interpreter, '-c', IMPORT_TEST.format(pkg.get('name'))]
    )
    return res == 0


def make_install(pkg, tempdir):
    """Configure, make, and make install packages"""
    cmds = (pkg.get('config'), pkg.get('build'), pkg.get('install'))
    pwd = os.getcwd()
    basename = pkg.get('src').rsplit('/', 1)[-1].split('.tar')[0]
    try:
        os.chdir(os.path.join(tempdir, basename))
        if not sum([subprocess.call(cmd) for cmd in cmds]) == 0:
            raise OSError('Failed to build `%s`' % basename)
    finally:
        os.chdir(pwd)


def main():
    """Script entrypoint"""
    if not os.path.isdir(VENV):
        raise OSError('No venv found')
    if not os.path.isfile(VENV_PY):
        raise OSError('No venv python interpreter found')

    try:
        tempdir = tempfile.mkdtemp()
        for pkg in (CAIRO, GOBJECT, LIBGLADE, GTK):
            if test_import(pkg, VENV_PY):
                print('%s already installed in venv' % pkg.get('name'))
            else:
                print('Downloading %s' % pkg.get('name'))
                download_and_unpack(pkg, tempdir)
                print('Installing %s' % pkg.get('name'))
                make_install(pkg, tempdir)
    finally:
        shutil.rmtree(tempdir)


if __name__ == '__main__':
    main()
