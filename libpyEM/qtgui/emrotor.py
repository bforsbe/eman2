#!/usr/bin/env python

#
# Author: Steven Ludtke (sludtke@bcm.edu)
# Copyright (c) 2000-2006 Baylor College of Medicine
#
# This software is issued under a joint BSD/GNU license. You may use the
# source code in this file under either license. However, note that the
# complete EMAN2 and SPARX software packages have some GPL dependencies,
# so you are responsible for compliance with the licenses of these packages
# if you opt to use BSD licensing. The warranty disclaimer below holds
# in either instance.
#
# This complete copyright notice must be included in any revised version of the
# source code. Additional authorship citations may be added, but existing
# author citations must be preserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston MA 02111-1307 USA
#
#

from PyQt4 import QtCore, QtGui, QtOpenGL
from PyQt4.QtCore import Qt
from weakref import WeakKeyDictionary

from OpenGL import GL,GLU,GLUT
from OpenGL.GL import *

import sys
from math import tan,pi
import time

from emfloatingwidgets import EMGLRotorWidget,EM3DWidget,EMGLViewQtWidget
from emimageutil import  EMEventRerouter
from emglobjects import EMOpenGLFlagsAndTools, EMImage2DGUIModule,EMOpenGLFlagsAndTools
from emapplication import EMStandAloneApplication, EMQtWidgetModule, EMGUIModule

class EMRotorWidget(QtOpenGL.QGLWidget,EMEventRerouter):
	"""A QT widget for rendering EMData objects. It can display stacks of 2D images
	in 'matrix' form on the display. The middle mouse button will bring up a
	control-panel. The QT event loop must be running for this object to function
	properly.
	"""
	allim=WeakKeyDictionary()
	def __init__(self,em_rotor_module,enable_timer=True):
		assert(isinstance(em_rotor_module,EMRotorModule))
		EMRotorWidget.allim[self]=0
		
		fmt=QtOpenGL.QGLFormat()
		fmt.setDoubleBuffer(True);
		fmt.setSampleBuffers(True)
		QtOpenGL.QGLWidget.__init__(self,fmt)
		EMEventRerouter.__init__(self)
		
		self.target = em_rotor_module
		
		self.setFocusPolicy(Qt.StrongFocus)
		
		self.fov = 30
		self.aspect = 1.0
		self.z_near = 1000
		self.z_far = 2000
		
		self.animatables = []
		
	
		if enable_timer:
			self.__init_timer()
		else: self.timer_enabled = False
		
		self.light_0_pos = [0.1,.1,1.,0.]
		
		self.polygon_smooth = True	

	def __init_timer(self):
		self.timer = QtCore.QTimer()
		QtCore.QObject.connect(self.timer, QtCore.SIGNAL("timeout()"), self.timeout)
		self.timer.start(20)
		self.timer_enabled = True
		
	def get_optimal_size(self):
		lr = self.target.get_suggested_lr_bt_nf()
		width = lr[1] - lr[0]
		height = lr[3] - lr[2]
		return [width+80,height+20]
	
	def timeout(self):
		if len(self.animatables) == 0: return
		for i,animatable in enumerate(self.animatables):
			try:
				if not animatable.animate(time.time()):
					# this could be dangerous
					self.animatables.pop(i)
			
			except: self.animatables.pop(i)
		self.updateGL()
		
	def register_animatable(self,animatable):
		self.animatables.append(animatable)

	def initializeGL(self):
		glClearColor(0,0,0,0)
		
		glLightfv(GL_LIGHT0, GL_AMBIENT, [0.1, 0.1, 0.1, 1.0])
		glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])
		glLightfv(GL_LIGHT0, GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
		glLightfv(GL_LIGHT0, GL_POSITION, self.light_0_pos)
	
		glEnable(GL_LIGHTING)
		glEnable(GL_LIGHT0)
		
		glEnable(GL_DEPTH_TEST)
		
		glEnable(GL_NORMALIZE)
		
		glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
		glHint(GL_TEXTURE_COMPRESSION_HINT, GL_NICEST)
		
		glEnable(GL_POLYGON_SMOOTH)
		glHint(GL_POLYGON_SMOOTH_HINT, GL_NICEST)
		
		if ( "GL_ARB_multisample" in glGetString(GL_EXTENSIONS) ):
			glEnable(GL_MULTISAMPLE)
		else: glDisable(GL_MULTISAMPLE)
		
	def paintGL(self):
		
		error = glGetError()
		if error != GL.GL_NO_ERROR:
			print "There is an error with opengl, not doing anything"
			return
		
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT )
		glLoadIdentity()
		if ( self.target == None ): return
		try:
			self.target.render()
		except: 
			print "render error"
			self.animatables = []

	
	def resizeGL(self, width, height):
		if width <= 0 or height <= 0: return None
		GL.glViewport(0,0,width,height)
	
		GL.glMatrixMode(GL.GL_PROJECTION)
		GL.glLoadIdentity()
		self.aspect = float(width)/float(height)
		GLU.gluPerspective(self.fov,self.aspect,self.z_near,self.z_far)
		GL.glMatrixMode(GL.GL_MODELVIEW)
		GL.glLoadIdentity()
		
		self.target.projection_or_viewport_changed()
	def set_near_far(self,near,far):
		self.z_near = near
		self.z_far = far
		
		GL.glMatrixMode(GL.GL_PROJECTION)
		GL.glLoadIdentity()
		GLU.gluPerspective(self.fov,self.aspect,self.z_near,self.z_far)
		#GL.glOrtho(0.0,width,0.0,height,-width,width)
		GL.glMatrixMode(GL.GL_MODELVIEW)
		GL.glLoadIdentity()
		
	def get_depth_for_height(self, height):
		# This function returns the width and height of the renderable 
		# area at the origin of the data volume
		depth = height/(2.0*tan(self.fov/2.0*pi/180.0))
	
		return depth
	
	def get_core_object(self):
		return self.target
	


class EMRotorModule(EMImage2DGUIModule):
	def get_qt_widget(self):
		if self.parent == None:
			self.parent = EMRotorWidget(self)
		return self.parent
	
	def __init__(self, data=None,application=None):
		EMImage2DGUIModule.__init__(self,application)
		self.parent = None
		try: self.parent.setAcceptDrops(True)
		except:	pass

		
		self.rotor = EMGLRotorWidget(self,0,-70,-15,EMGLRotorWidget.TOP_ROTARY,100)
		self.rotor.set_angle_range(40.0)
		self.rotor.set_mouse_mode("mxrotor")
		self.widget = EM3DWidget(self,self.rotor)
		self.widget.set_draw_frame(False)
		
		self.z_near = 0
		self.z_far = 0
		
		self.inspector = None
		
	def render(self):
		lr = self.rotor.get_suggested_lr_bt_nf()
		z = self.parent.get_depth_for_height(abs(lr[3]-lr[2]))
		lrt = self.widget.get_lr_bt_nf()
		
		z_near = z-lrt[4]
		z_trans = 0
		z_far = z-lrt[5]
		if z_near < 0:
			z_trans = z_near
			z_near = 1
			z_far -= z_trans
		if z_far < 0: z_far = 0.1 # hacking alert
		z_far += abs(lr[3]-lr[2]) # hacking alert
		if self.z_near != z_near or self.z_far != z_far:
			self.z_near = z_near
			self.z_far = z_far
			self.parent.set_near_far(self.z_near,self.z_far)

		#print -self.parent.get_depth_for_height(abs(lr[3]-lr[2])),self.z_near,self.z_far,abs(lr[3]-lr[2])
		glPushMatrix()
		glTranslate(-(lr[1]+lr[0])/2.0,-(lr[3]+lr[2])/2.0,-self.parent.get_depth_for_height(abs(lr[3]-lr[2]))+z_trans+abs(lr[3]-lr[2]))
		self.widget.draw()
		glPopMatrix()
	
	def updateGL(self):
		try: self.parent.updateGL()
		except: pass
		
	def mousePressEvent(self, event):
		if event.button()==Qt.MidButton:
			pass
			#self.show_inspector(True)
		else:
			self.widget.mousePressEvent(event)
	
	def mouseMoveEvent(self, event):
		self.widget.mouseMoveEvent(event)
		
	def mouseReleaseEvent(self, event):
		self.widget.mouseReleaseEvent(event)
		
	def wheelEvent(self, event):
		self.widget.wheelEvent(event)
		
	def dragEnterEvent(self,event):
		pass

	def get_inspector(self): return None

	def dropEvent(self,event):
		pass
	
	def get_core_object(self):
		pass
	
	def add_file_dialog(self):
		fd = QtGui.QFileDialog(self.parent,"Open File",QtCore.QDir.currentPath(),QtCore.QString("Image files (*.img *.hed *.mrc)"))
		fd.show()
		fd.hide()

		self.add_qt_widget(fd)
	def keyPressEvent(self,event):
		if event.key() == Qt.Key_0:
			self.add_file_dialog()
			
	def add_qt_widget(self,qt_widget):
		a = EMGLViewQtWidget(self.parent)
		a.setQtWidget(qt_widget)
		self.rotor.add_widget(a)
			
	def width(self):
		return self.parent.width()
	
	def height(self):
		return self.parent.height()
	
	def register_animatable(self,animatable):
		self.parent.register_animatable(animatable)
	
	def projection_or_viewport_changed(self):
		self.rotor.resize_event(-1,1)
	
if __name__ == '__main__':
	em_app = EMStandAloneApplication()
	window = EMRotorModule(application=em_app)
	window.get_qt_widget()
	window.add_file_dialog()
	window.add_file_dialog()
	window.add_file_dialog()
	em_app.show()
	em_app.execute()	

