#!/usr/bin/env python

# Author: Michael Bell,jmbell@bcm.edu
# Date: 8/5/2016

import os
import errno
import shutil

progs_contain = ["em","EM","","EMAN","eman","e2"]

# standard library plus a few commonly used packages
pylibs = """abc,anydbm,argparse,array,asynchat,asyncore,atexit,base64,BaseHTTPServer,
bisect,bz2,calendar,cgitb,cmd,codecs,collections,commands,compileall,ConfigParser,contextlib,
Cookie,copy,cPickle,cProfile,cStringIO,csv,datetime,dbhash,dbm,decimal,difflib,dircache,dis,
doctest,dumbdbm,EasyDialogs,errno,exceptions,filecmp,fileinput,fnmatch,fractions,functools,
gc,gdbm,getopt,getpass,gettext,glob,grp,gzip,hashlib,heapq,hmac,imaplib,inspect,itertools,
json,linecache,locale,logging,mailbox,math,mhlib,mmap,multiprocessing,operator,optparse,os,
pdb,pickle,pipes,pkgutil,platform,plistlib,pprint,profile,pstats,pwd,pyclbr,pydoc,Queue,
random,re,types,readline,resource,rlcompleter,robotparser,sched,select,shelve,shlex,shutil,signal,
SimpleXMLRPCServer,site,sitecustomize,smtpd,smtplib,socket,SocketServer,sqlite3,string,
StringIO,struct,subprocess,sys,sysconfig,tabnanny,tarfile,tempfile,textwrap,threading,time,
timeit,trace,traceback,unittest,urllib,urllib2,urlparse,usercustomize,uuid,warnings,weakref,
webbrowser,whichdb,xml,xmlrpclib,zipfile,zipimport,zlib,builtins,__builtin__,bsddb,PyQt4,
OpenGL,numpy,scipy,matplotlib,readline,ipython,IPython,mpi,mpi4py,setuptools,theano,build,pylab,
pywin32,colorsys,wx,psutil,imp,sets,testlib,function,fcntl,msvcrt,ntpath,new,win32api"""
pylibs = pylibs.replace("\n","").split(",") # clean up and convert to list

bindir_files = [i.replace(".py","") for i in os.listdir("./programs")]
sparxlibs = [n.replace(".py","") for n in os.listdir("sparx/libpy/") if "__" not in n] + ["amoeba","reconstructions"]

donotedit = ["build.py","setup.py","refactor.py","install-dependencies.py"]
donotenter = ["doc","images","fonts","recipes","build","latex","modular_class_html"]

def main():
	olddir = os.getcwd()
	newdir = "../{}-refactor".format(os.path.basename(olddir))

	global bindir_files
	bindir_files = [i.replace(".py","") for i in os.listdir("./programs")]

	for root,dirs,files in os.walk(olddir,topdown=True):
		print("\n\nCWD: {}\n\n".format(root))

		newroot = root.replace(olddir,newdir)
		mkdir_p(newroot)

		for f in files:
			if os.path.isfile("{}/{}".format(root,f)): # if this isn't a file, there's a serious problem.
				# ONLY edit python files. Otherwise, ONLY copy contents of these directories and DONT edit build, setup, or refactor scripts.
				if f[-3:] == ".py" and root not in donotenter and f not in donotedit:
					with open("{}/{}".format(root,f),'r') as inf:
						file_content = inf.read() # read python file from origin
					file_content = fix_imports(file_content) # fix import statements in this file
					with open("{}/{}".format(newroot,f),'w') as outf:
						outf.write(file_content) # write edited file content to target (newroot)
				else:
					try: 
						shutil.copy("{}/{}".format(root,f),"{}/{}".format(newroot,f)) # try copying file from origin to target
					except:
						try:
							os.unlink("{}/{}".format(newroot,f)) # probably already exists at location, so we remove it from target
							shutil.copy("{}/{}".format(root,f),"{}/{}".format(newroot,f)) # and try copying again from origin to target
						except:
							print("ERROR COPYING FILE: {}".format(f))
							sys.exit(1)

	print("Results stored in: {}".format(newdir))

def mkdir_p(path):
	try: os.makedirs(path)
	except OSError as exc:
		if exc.errno == errno.EEXIST and os.path.isdir(path): pass
		else: raise

def fix_imports(lines):
	newlines = lines.split("\n")
	flag = False
	for i,l in enumerate(newlines):
		if l != "" and l.strip() != "": # we don't care about blank lines
			if l.strip()[0] != "#": # we don't want whole line comments
				if "import " in l and l.strip()[0] != "#": # is this an import statement?
					if "=" not in l: # import statements don't contain =
						old = l.strip()
						new = get_new_import(old)
						newlines[i] = l.replace(old,new)
	return "\n".join(newlines)

def insert(s,i,x):
	return s[:x]+i+s[x:]

def split_prefix(imp):
	loc = [imp.find("from"),imp.find("import")]
	try: start = min([l for l in loc if l >=0])
	except:
		print("PROBABLY NOT AN IMPORT: {}".format(imp))
		start = 0 
	return imp[:start],imp[start:]

def get_new_import(imp):
	prefix,oldimp = split_prefix(imp) # split anything before the actual import statement for easier string comparison
	#print("prefix: {}\nimp: {}".format(prefix,oldimp))
	oldimp = " ".join(oldimp.split()) # Extra spaces in import statements make string comparisons annoying. I'm getting rid of them.

	if ".." in oldimp:
		print("RELATIVE IMPORT: {}".format(imp))
		newimp = oldimp # leave relative imports alone. pretty sure we want them as-is.
	elif "-" in oldimp:
		newimp = oldimp
		print("NOT AN IMPORT: {}".format(newimp))
	elif any([s in oldimp for s in bindir_files]):  
		newimp = oldimp # program in bin, so import doesn't need to be altered
		print("BIN PROGRAM: {}".format(newimp))
	elif any([s in oldimp for s in sparxlibs]):
		if "libpy" in oldimp:
			newimp = "from sparx import *"
		else:
			newimp = fix_import(oldimp,"sparx")
	else:
		newimp = fix_import(oldimp,"EMAN2")
	return "{}{}".format(prefix,newimp)

def fix_import(oldimp,libname):
	if oldimp.find("from") == 0: # case 1: from module import blah
		if oldimp != "from {} import *".format(libname):
			if not any(["from {}".format(s) in oldimp for s in pylibs]):
				if "from {} import".format(libname) in oldimp:
					newimp = oldimp
					print("FROM IMPORT: {}".format(newimp))
				else:
					newimp = insert(oldimp,"{}.".format(libname),len("from ")) # replace "from module" with "from libname.module"
					print("FROM INSERT: {}".format(newimp))
			elif any([s in oldimp for s in sparxlibs]):
				newimp = insert(oldimp,"{}.".format(libname),len("from ")) # replace "from module import blah" with "from libname.module import blah"
				print("SPARXLIB: {}".format(newimp))
			else:
				newimp = oldimp
				print("STDLIB: {}".format(newimp)) # leave non-EMAN/sparx imports alone.
		else: 
			newimp = oldimp
			print("GLOB FROM IMPORT: {}".format(oldimp))
	elif oldimp.find("import") == 0: # case 2: import module or import module as blah
		if oldimp == "import {}".format(libname): # we just use the existing import
			newimp = oldimp
		elif any(["import {}".format(s) in oldimp for s in pylibs]):
			newimp = oldimp # if it's important from stdlib, we don't want to change it
		else:
			if oldimp.split(" ")[1] in bindir_files:
				newimp = oldimp # we don't need to change how we import programs in the bin directory
			elif " as " in oldimp:
				newimp = insert(oldimp,"{}.".format(libname),len("import ")) # replace "import module as x" with "import libname.module as x"
				print("IMPORT INSERT: {}".format(newimp))
			else:
				m = oldimp.replace("import ","")
				if "," in m:
					if "\\" in oldimp or '"' in oldimp or "(" in oldimp or ")" in oldimp:
						newimp = oldimp 
						print("PUNCTUATION: {}".format(newimp))
					else:
						newimp = "from {} import {}".format(libname,m)
						print("COMMA IMPORT: {}".format(newimp))
				else:
					if len(m.split(".")) > 1:
						#import pyemtbx.options -> from EMAN2.pyemtbx import options
						module = ".".join(m.split(".")[:-1])
						submod = m.split(".")[-1]
						newimp = "from {lib}.{parent} import {child}".format(lib=libname,parent=module,child=submod)
						print("LONG IMPORT {}".format(newimp))
					else:
						if "\\" in oldimp or '"' in oldimp or "(" in oldimp or ")" in oldimp:
							newimp = oldimp 
							print("PUNCTUATION: {}".format(newimp))
						else:
							newimp = "import {lib}.{module} as {module}".format(lib=libname,module=m)
							print("SHORT IMPORT: {}".format(newimp))
	else: 
		newimp = oldimp # otherwise leave import alone... this case is likely to unforeseen catch errors.
		print("POSSIBLE ERROR: {}".format(oldimp))
	return newimp

if __name__ == "__main__":
	main()
