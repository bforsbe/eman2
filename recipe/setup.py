from setuptools import setup, find_packages
import glob
import os
import shutil


root='setup_dir'
# libdir=os.path.join('C:',ro,'lib')
libdir=os.path.join(root,'lib')
bindir=os.path.join(root,'bin')

shutil.rmtree('build',ignore_errors=True)
shutil.rmtree('dist',ignore_errors=True)

if os.path.isdir('setup_dir_copy'):
	print "rmtree: %s" % os.path.abspath('setup_dir_copy')
	shutil.rmtree('setup_dir_copy')

print "copytree: %s -> %s" % (os.path.abspath('setup_dir'),os.path.abspath('setup_dir_copy'))
shutil.copytree('setup_dir', 'setup_dir_copy')

root='setup_dir_copy'
libdir=os.path.join(root,'lib')
bindir=os.path.join(root,'bin')

print "move: %s -> %s" % (os.path.join(libdir,'EMAN2.py'),os.path.join(libdir,'__init__.py'))
shutil.move(os.path.join(libdir,'EMAN2.py'),os.path.join(libdir,'__init__.py'))

shutil.copytree(bindir, os.path.join(libdir,'bin'))
for f in os.listdir(bindir):
	print "  --- move: %s -> %s" % (os.path.abspath(os.path.join(bindir,f)),os.path.abspath(libdir))
	shutil.move(os.path.join(bindir,f),libdir)

os.mkdir(os.path.join(libdir,'lib'))

e2_pkgdata = [os.path.join('lib','pmconfig'), 'doc', 'examples', 'fonts', 'images', 'test']
for d in e2_pkgdata:
	print "  --- move: %s -> %s" % (os.path.abspath(os.path.join(root, d)),os.path.abspath(os.path.join(libdir,'lib')))
	shutil.move(os.path.join(root, d),os.path.join(libdir,'lib'))

sx_scripts = []
e2_scripts = ["%s=EMAN2.%s:main" % (os.path.splitext(os.path.basename(name))[0],os.path.splitext(os.path.basename(name))[0])
			  for name in glob.glob(os.path.join(libdir,'e2*.py'))
			  if not name.endswith('__init__.py')
			  ]

e2_pkgdata = [os.path.join('lib',d,'*') for d in e2_pkgdata]
e2_pkgdata.extend(['*.so', '*.pyd', '*.dylib', os.path.join('lib','pmconfig','*'), os.path.join('bin','*')])
sx_pkgdata = []

print "e2_pkgdata: %s" % e2_pkgdata
print "e2_scripts: %s" % e2_scripts

setup(
	name="eman2",
	version="3.2",

	package_dir={'':root, 'EMAN2':libdir},
	packages=['EMAN2', 'EMAN2.pyemtbx'],
	# packages=find_packages(libdir),
	package_data={'EMAN2':e2_pkgdata,},
	include_package_data = True,
	# scripts = e2_scripts + sx_scripts,
	entry_points={
		'console_scripts': [
							   'eman2=EMAN2.eman2:main',
							   'erase_gold=EMAN2.erase_gold:main',
						   ] + e2_scripts,
	},
    
    zip_safe = False,

	description="A scientific image processing software suite with a focus on CryoEM and CryoET",
	author="Steve Ludtke",
	author_email="sludtke@bcm.edu",
	license="GNU General Public License, Version 2",
	url="http://blake.bcm.edu/emanwiki/EMAN2",
)
