#!/usr/bin/env python
#
# Author: David Woolford (woolford@bcm.edu)
# Copyright (c) 2000-2006 Baylor College of Medicine


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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  2111-1307 USA
#
#

from emboxerbase import *
from valslider import ValSlider
from EMAN2 import BoxingTools,gm_time_string,Transform
from pyemtbx.boxertools import CoarsenedFlattenedImageCache,FLCFImageCache
from copy import deepcopy

SWARM_TEMPLATE_MIN = TEMPLATE_MIN # this comes from emboxerbase

def main():
	progname = os.path.basename(sys.argv[0])
	usage = """%prog [options] <image> <image2>....

a refactoring of e2boxer
"""

	parser = OptionParser(usage=usage,version=EMANVERSION)
	parser.add_option("--boxsize","-B",type="int",help="Box size in pixels",default=128)
	
	(options, args) = parser.parse_args()
	
	error_message = check(options,args)
	if len(error_message) > 0:
		error = "\n"
		for e in error_message:
			error += "Error: "+e +"\n"
		parser.error(error)
		
	args = [abs_path(arg) for arg in args] # always try to use full file names 

	application = EMStandAloneApplication()
#	QtCore.QObject.connect(gui, QtCore.SIGNAL("module_idle"), on_idle)
	
	module = EMBoxerModule(args,options.boxsize)
	module.show_interfaces()
	# this is an example of how to add your own custom tools:
	module.add_tool(SwarmTool,particle_diameter=options.boxsize)
	application.execute()

def gen_rot_ave_template(image_name,ref_boxes,shrink,box_size,iter=4):
	
	ptcls = []
	mediator = SwarmShrunkenImageMediator(box_size/(2*shrink),shrink)
	
	real_box_size = box_size/shrink
	averages = []
	for box in ref_boxes:
		if box.in_template == False: continue # it's excluded from the template
		
		xc = box.x/shrink-real_box_size/2
		yc = box.y/shrink-real_box_size/2
		r = Region(xc,yc,real_box_size,real_box_size)
		image = CoarsenedFlattenedImageCache.get_image(box.image_name,mediator)
		particle = image.get_clip(r)
		
		particle.process_inplace("normalize.edgemean")
		ptcls.append(particle)
		
	if len(ptcls) == 0:
		raise RuntimeError("No boxes are flagged as contributing to the template")
	
	# bootstrap the original average 
	ave = ptcls[0].copy()
	for i in range(1,len(ptcls)):
		ta = ptcls[i].align("translational",ave)
		ave.add(ta)
	
	ave.process_inplace("xform.centeracf")
	ave.process_inplace("math.radialaverage")
	ave.process_inplace("normalize.edgemean")
	ave.process_inplace("mask.sharp",{'outer_radius':ave.get_xsize()/2})
	averages.append(ave)
	averages[-1].set_attr("creation_time_stamp", gm_time_string())
	for n in range(0,iter):
		t = []
		for idx,particle in enumerate(ptcls):
			ta = particle.align("translational",ave)
			t.append(ta)
			
	
		ave = t[0].copy()
		for i in range(1,len(ptcls)):
			ave.add(t[i])
			
		ave.process_inplace("xform.centeracf")
		ave.process_inplace("math.radialaverage")
		ave.process_inplace("normalize.edgemean")
		
		# edge normalize here SL before
		ave.process_inplace("mask.sharp",{'outer_radius':ave.get_xsize()/2})
		averages.append(ave)
		averages[-1].set_attr("creation_time_stamp", gm_time_string())
		
	return averages


class SwarmShrunkenImageMediator:
	def __init__(self,template_radius,subsample_rate):
		self.template_radius = template_radius
		self.subsample_rate = subsample_rate
	
	def get_template_radius(self): return self.template_radius
	def get_subsample_rate(self): return self.subsample_rate

class SwarmFLCFImageMediator:
	def __init__(self,template_radius,subsample_rate,template_image):
		self.template_radius = template_radius
		self.subsample_rate = subsample_rate
		self.template_object = SwarmFLCFImageMediator.TemplateObject(template_image)
	
	def get_template_radius(self): return self.template_radius
	def get_subsample_rate(self): return self.subsample_rate
	def get_template_object(self): return self.template_object
	
	class TemplateObject:
		def __init__(self,template_image):
			self.template_image = template_image
			
		def get_template_ts(self): return self.template_image["creation_time_stamp"]
		
		def get_template(self): return self.template_image

		def get_radius(self): return
		
class SwarmBox:
	def __init__(self,x,y,image_name,in_template=True,profile=None):
		self.x = x
		self.y = y
		self.in_template = in_template
		self.image_name = image_name
		self.profile=profile
		self.peak_x = None
		self.peak_y = None
		self.peak_score = None
		self.ever_moved = False # used to record if the user ever moved the ref after they first added it
	
	def type_name(self):
		if self.in_template: return SwarmBoxer.REF_NAME
		else: return SwarmBoxer.WEAK_REF_NAME
	
	def update_picking_data(self,mediator):
		
		shrink = mediator.get_subsample_rate()
		x = int(self.x/shrink)
		y = int(self.y/shrink)
		search_radius = mediator.get_template_radius()
		correlation = FLCFImageCache.get_image(self.image_name,mediator)
		
		peak_location = BoxingTools.find_radial_max(correlation,x,y,search_radius )
		peak_location2 = BoxingTools.find_radial_max(correlation,peak_location[0],peak_location[1],search_radius )
		if (peak_location != peak_location2):
			# there is no local max, this particle will be ignorned
			self.profile = None
			self.peak_score = None
			self.peak_x = None
			self.peak_y = None
			return
	
		# store the peak location
		self.peak_x = peak_location[0]
		self.peak_y = peak_location[1]
	
		# store the correlation value at the correlation max
		self.peak_score = correlation.get(self.peak_x,self.peak_y)
		
		if self.peak_score != None:
			# store the profile
			self.profile = BoxingTools.get_min_delta_profile(correlation,self.peak_x,self.peak_y, mediator.get_template_radius() )
	
	
class SwarmPanel:
	def __init__(self,target,particle_diameter=128):
		self.busy = True
		self.particle_diameter = particle_diameter
		self.target = weakref.ref(target)
		self.widget = None
		self.busy = False
		
	def get_widget(self):
		if self.widget == None:
			from PyQt4 import QtCore, QtGui, Qt
			self.widget = QtGui.QWidget()
			vbl = QtGui.QVBoxLayout(self.widget)
			vbl.setMargin(0)
			vbl.setSpacing(6)
			vbl.setObjectName("vbl")
			
			hbl = QtGui.QHBoxLayout()
			ptcl_diam_label = QtGui.QLabel("Particle Diameter:")
			ptcl_diam_label.setToolTip("An estimate of the particle diameter - this used by Swarm for automatically shrinking, and for estimating parameters.")
			hbl.addWidget(ptcl_diam_label)
			
			self.ptcl_diam_edit = QtGui.QLineEdit(str(self.particle_diameter))
			hbl.addWidget(self.ptcl_diam_edit)
			self.clear=QtGui.QPushButton("Clear Boxes")
			self.clear.setToolTip("Clear boxes generated by the Swarm mode.")
			hbl.addWidget(self.clear)
			
			vbl.addLayout(hbl)
			
			self.thrbut = QtGui.QRadioButton(SwarmBoxer.THRESHOLD)
			self.selbut = QtGui.QRadioButton(SwarmBoxer.SELECTIVE)
			self.selbut.setChecked(True)
			self.morselbut = QtGui.QRadioButton(SwarmBoxer.MORESELECTIVE)
			
			self.method_group = QtGui.QButtonGroup()
			self.method_group.addButton(self.thrbut)
			self.method_group.addButton(self.selbut)
			self.method_group.addButton(self.morselbut)
			
			self.methodhbox = QtGui.QHBoxLayout()
			self.methodhbox.addWidget(self.thrbut)
			self.methodhbox.addWidget(self.selbut)
			self.methodhbox.addWidget(self.morselbut)
			
			self.groupbox = QtGui.QGroupBox("Auto Box Method")
			self.groupbox.setToolTip("Tell Swarm what criteria to use for selecting particles.")
			self.groupbox.setLayout(self.methodhbox)
			vbl.addWidget(self.groupbox)
			
			hbl_ww = QtGui.QHBoxLayout()
			self.view_template=QtGui.QPushButton( QtGui.QIcon(get_image_directory() + "pp_boxer_icon.png"),"View Template")
			self.view_template.setEnabled(False)
			self.view_template.setToolTip("View the template that is being used (if more than one template is shown, it is the last one).")
			hbl_ww.addWidget(self.view_template)
			
			self.autobox=QtGui.QPushButton(QtGui.QIcon(get_image_directory() + "green_boxes.png"),"Autobox")
			self.autobox.setEnabled(False)
			self.autobox.setToolTip("Force Swarm to autobox the current image")
			hbl_ww.addWidget(self.autobox)
			
			vbl.addLayout(hbl_ww)
			
			hbl_aa = QtGui.QHBoxLayout()
			self.update_template = QtGui.QCheckBox("Refresh Template")
			self.update_template.setToolTip("Whether or not the act of adding a reference should force an update of the template being used by Swarm.\nOnce you have an adequate template you can turn this off and interactive picking will be faster.")
			self.update_template.setChecked(True)
			hbl_aa.addWidget(self.update_template)
			
			
			self.auto_update = QtGui.QCheckBox("Auto Box Update")
			self.auto_update.setToolTip("Whether or not autoboxing should occur every time you change a parameter. This is the old dynapix button.")
			self.auto_update.setChecked(True)
			hbl_aa.addWidget(self.auto_update)
			vbl.addLayout(hbl_aa)
			
			
			self.advanced_hbl2 = QtGui.QHBoxLayout()
			self.enable_interactive_threshold  = QtGui.QCheckBox("Interactive Threshold")
			self.enable_interactive_threshold.setToolTip("Tweak the correlation threshold that is used to select particles.")
			self.enable_interactive_threshold.setChecked(False)
			self.thr = ValSlider(None,(0.0,3.0),"")
			self.thr.setValue(1.0)
			self.thr.setEnabled(False)
			self.advanced_hbl2.addWidget(self.enable_interactive_threshold)
			self.advanced_hbl2.addWidget(self.thr)
			vbl.addLayout(self.advanced_hbl2)
			
			hbl_bb = QtGui.QHBoxLayout()
			self.step_back=QtGui.QPushButton("Step Back")
			self.step_back.setToolTip("Recall the previous Swarm states")
			self.step_back.setEnabled(False)
			hbl_bb.addWidget(self.step_back)
			self.step_forward=QtGui.QPushButton("Step Forward")
			self.step_forward.setToolTip("Undo a step back")
			self.step_forward.setEnabled(False)
			hbl_bb.addWidget(self.step_forward)
			vbl.addLayout(hbl_bb)
			
		
			QtCore.QObject.connect(self.ptcl_diam_edit,QtCore.SIGNAL("editingFinished()"),self.new_ptcl_diam)
			QtCore.QObject.connect(self.update_template,QtCore.SIGNAL("clicked(bool)"),self.update_template_checked)
			QtCore.QObject.connect(self.auto_update,QtCore.SIGNAL("clicked(bool)"),self.auto_update_checked)
			QtCore.QObject.connect(self.clear, QtCore.SIGNAL("clicked(bool)"), self.clear_clicked)
			QtCore.QObject.connect(self.view_template, QtCore.SIGNAL("clicked(bool)"), self.view_template_clicked)
			QtCore.QObject.connect(self.autobox, QtCore.SIGNAL("clicked(bool)"), self.auto_box_clicked)
			QtCore.QObject.connect(self.method_group,QtCore.SIGNAL("buttonClicked (QAbstractButton *)"),self.method_group_clicked)
			QtCore.QObject.connect(self.enable_interactive_threshold, QtCore.SIGNAL("clicked(bool)"), self.interact_thresh_clicked)
			QtCore.QObject.connect(self.thr,QtCore.SIGNAL("sliderReleased"),self.new_threshold_release)
			QtCore.QObject.connect(self.step_back, QtCore.SIGNAL("clicked(bool)"), self.step_back_clicked)
			QtCore.QObject.connect(self.step_forward, QtCore.SIGNAL("clicked(bool)"), self.step_forward_clicked)
			
		return self.widget
	
	def update_states(self,swarm_boxer):
		self.busy = True
		self.ptcl_diam_edit.setText(str(swarm_boxer.particle_diameter))
		mode = swarm_boxer.pick_mode
		if mode == SwarmBoxer.THRESHOLD: self.thrbut.setChecked(True)
		elif mode == SwarmBoxer.SELECTIVE: self.selbut.setChecked(True)
		elif mode == SwarmBoxer.MORESELECTIVE: self.morselbut.setChecked(True)
		else: raise RuntimeError("This shouldn't happen")
		self.update_template.setChecked(swarm_boxer.update_template)
		self.auto_update.setChecked(swarm_boxer.auto_update)
		t = swarm_boxer.peak_score
		if swarm_boxer.interactive_threshold != None:
			t = swarm_boxer.interactive_threshold
			self.enable_interactive_threshold.setChecked(True)
			self.thr.setEnabled(True)
		else:
			self.enable_interactive_threshold.setChecked(False)
			self.thr.setEnabled(False)
		self.set_picking_data(t,swarm_boxer.profile,swarm_boxer.profile_trough_point)
		
		#self.busy = True # BEWARE self.set_picking_data set it False!
		
		self.busy = False

	
	def new_threshold_release(self,val):
		val = float(val)
		self.target().set_interactive_threshold(val)
	
	def interact_thresh_clicked(self,val):
		self.thr.setEnabled(val)
		if val == False:
			self.target().disable_interactive_threshold()
	
	def set_picking_data(self,threshold,profile=[],trough_point=None):
		self.busy = True
		if threshold == None: self.thr.setValue(0)
		else: self.thr.setValue(threshold)
		help = ""
		if profile != None and len(profile) > 0:
			help += "The Swarm profile is ["
			for i,p in enumerate(profile):
				if i != 0: help += " "
				help += "%.3f" %p
				
			help += "]\n"
				
		if trough_point: 
			help += "The trough point is " + str(trough_point) + "."
		
		self.thr.setToolTip(help)
		self.busy = False
	
	def new_ptcl_diam(self):
		if self.busy: return
		self.target().set_particle_diameter(int(self.ptcl_diam_edit.text()))
		
	def update_template_checked(self,val):
		if self.busy: return
		self.target().set_update_template(val)
		
	def clear_clicked(self,val):
		self.target().clear_all()
		
	def method_group_clicked(self,button):
		if self.busy: return
		self.target().set_pick_mode(str(button.text()))	
		
	def view_template_clicked(self,val):
		self.target().view_template_clicked()
		
	def auto_box_clicked(self,val):
		self.target().auto_box_clicked()

	def enable_view_template(self,val):
		self.view_template.setEnabled(val)
		
	def auto_update_checked(self,val):
		if self.busy: return
		self.target().set_auto_update(val)
	
	def enable_auto_box(self,val):
		self.autobox.setEnabled(val)
		
	def	step_back_clicked(self,val):
		self.target().step_back()
	
	def step_forward_clicked(self,val):
		self.target().step_forward()
		
	def enable_step_back(self,val,total=None):
		self.step_back.setEnabled(val)
		if total != None: self.step_back.setToolTip("%d backward steps in the stack" %total)
		else: self.step_back.setToolTip("")
		
	def enable_step_forward(self,val,total=None):
		if self.widget == None: self.get_widget()
		self.step_forward.setEnabled(val)
		if total != None: self.step_forward.setToolTip("%d forward steps in the stack" %total)
		else: self.step_forward.setToolTip("")
	
def compare_box_correlation(box1,box2):
	c1 = box1[3]
	c2 = box2[3]
	if c1 > c2: return -1
	elif c1 == c2: return 0
	else: return 1


class SwarmBoxer:
	THRESHOLD = "Threshold"
	SELECTIVE = "Selective"
	MORESELECTIVE = "More Selective"
	CACHE_MAX = 10 # Each image has its last CACHE_MAX SwarmBoxer instance stored (or retrievable) automatically 
	PROFILE_MAX = 0.8 # this is a percentage - it stops the profile trough point from going to the end
	REF_NAME = "swarm_ref"
	AUTO_NAME = "swarm_auto"
	WEAK_REF_NAME = "swarm_weak_ref"
	EMBox.set_box_color(REF_NAME,[0,0,0])
	EMBox.set_box_color(WEAK_REF_NAME,[0.2,0.2,0.4])
	EMBox.set_box_color(AUTO_NAME,[0.4,.9,.4]) # Classic green, always was this one ;)
	MVT_THRESHOLD = 200 # a squared distance - used by the movement cache to automatically update using previously supplied user movement data
	SWARM_BOXERS = "swarm_boxers"
	SWARM_FWD_BOXERS = "swarm_fwd_boxers"
	SWARM_USER_MVT = "swarm_user_mvt"
	def __init__(self,particle_diameter=128):
		self.particle_diameter = particle_diameter
		self.update_template = True # Tied to the SwarmPanel - Whether or not the act of adding a reference should force an update of the template
		self.pick_mode = SwarmBoxer.SELECTIVE	# the autobox method - see EMData::BoxingTools for more details
		self.interactive_threshold = None  # Tied to the SwarmPanel -  this is a float when the user is playing with the threshold, but is None elsewise
		self.reset() # the first time this is called this establishes attribute variables - seeing as the function is required more than once it makes sense to do this
		self.auto_update = True # Tied to the SwarmPanel - this is the historical 'dynapix' button. It means that if any picking parameter is altered then autoboxing will be automatically triggered 
		self.signal_template_update = False
		
		BoxingTools.set_mode(BoxingTools.CmpMode.SWARM_AVERAGE_RATIO) # this probably never needs to change - this mode has the best statistics
	
		self.template_viewer = None
		
		self.step_back_cache = [] # this will stored lists that store the parameters necessary to reconstruct a swarm boxer
		self.step_fwd_cache = [] # this will store the redo lists
		self.mvt_cache = [] # we have to remember if any of the auto selected boxes were moved, so if the user reboxes then the movements they previously supplied will be applied
#		self.auto_center_list = [] # a list of box number which automatically gets center and then cleared in the update_parameters function
		
	def __del__(self):
		'''
		Closes the template viewer if it exists
		'''
		print "del sb"
		if self.template_viewer != None:
			self.template_viewer.closeEvent(None)
			self.template_viewer = None
	
	def reset(self):
		'''
		Sets the self.ref_boxes, self.templates, self.profile, self.peak_score and self.profile_trough_point to safe defaults.
		Called in a couple of locations internally (notable, in the __init__ function)
		'''
		self.ref_boxes = []
		self.templates = None
		self.profile = None
		self.peak_score = None
		self.profile_trough_point = None
	
	def to_list(self):
		'''
		Stores the vital variable attributes of this object in a list - returns a deep copy. The list contains these entries:
		-----------------------------
		Index   Variable			Description
		0		self.ref_boxes		List of SwarmBox object - this information could technically be used to regenerate the template and the picking parameters
		1		self.templates		List of EMData objects which are iteratively honed templates - the last is the one that was used for the correlation image
		2		self.profile		List of floats - The Swarm profile
		3		self.peak_score		Float - The correlation threshold being used to select particles
		4		self.profile_trough_point	Int - The trough point, used in the selective mode of Swarm picking
		5		self.particle_diameter		Int- User supplied estimate of the particle diameter
		6		self.update_template		Bool - Flag indicating whether adding a references should cause an update of the template
		7		self.pick_mode				Int - either SwarmBoxer.THRESHOLD, SwarmBoxer.SELECTIVE, or SwarmBoxer.MORESELECTIVE 
		8		self.interactive_threshol	Float or None - If not None, this is a theshold value that overrides self.peak_score
		9		self.auto_update			Bool - Whether changing the state of the SwarmBoxer should cause an auto update, i.e. when interacting in the interface
		10		unique id					String - that which is return by gm_time_string - this can be used to decide what is the best autoboxer (i.e. is not really related to interactive boxing)
		-----------------
		Note that it would be possible to append entries, but that if you disrupt the order which is specified above you will destroy back compatibility
		'''
		l = [self.ref_boxes,self.templates,self.profile,self.peak_score,self.profile_trough_point,self.particle_diameter,self.update_template]
		l.extend([self.pick_mode, self.interactive_threshold,self.auto_update, gm_time_string()])
		return deepcopy(l)
		
	def load_from_list(self,l):
		'''
		Sets almost every variable attributes to a new value by assuming a specific ordering of the incoming list.
		The incoming list should almost certainly have been generated, at some point in time, but the call to self.to_list -
		See the comments in self.to_list for more details.
		@param l a list that was almost certainly generated, at some point in time, but a call to self.to_list
		'''
		
		self.ref_boxes = l[0]
		self.templates = l[1]
		self.profile = l[2]
		self.peak_score = l[3]
		self.profile_trough_point = l[4]
		self.particle_diameter = l[5]
		self.update_template = l[6]
		self.pick_mode = l[7]
		self.interactive_threshold = l[8]
		self.auto_update = l[9]
		# entry 10 is not required, it is the creation stamp used to ascertain if common boxer instances are being used by different images, it has no relevance to interactive boxing
		
	def step_back(self):
		'''
		That which is called by the SwarmPanel when "Step Back" is clicked
		Manages all the various scenarios
		'''
		
		if len(self.step_back_cache) == 0: raise RuntimeError("Step backward cache has no entries")
		l = self.step_back_cache.pop(-1)
		self.step_fwd_cache.append(l)
		self.panel_object.enable_step_forward(True,len(self.step_fwd_cache))
		
		if len(self.step_back_cache) > 0:
			self.panel_object.enable_step_back(True,len(self.step_back_cache))
			self.load_from_last_state()
		else:
			self.target().clear_boxes([SwarmBoxer.REF_NAME,SwarmBoxer.AUTO_NAME,SwarmBoxer.WEAK_REF_NAME])
			self.reset()
			self.panel_object.enable_step_back(False)
			self.target().get_2d_window().updateGL()
			 
		self.panel_object.update_states(self)
		if self.template_viewer != None:
			self.template_viewer.set_data(self.templates,soft_delete=True)
			self.template_viewer.updateGL()
	
		if self.templates != None:
			self.panel_object.enable_view_template(True)
		
#		self.debug_back("back")
#		
#	def debug_back(self,s):
#		for i,c in enumerate(self.step_back_cache):
#			for j,b in enumerate(c[0]):
#				print s,i,j,b.in_template
#		print "---"
		
	def load_from_last_state(self):
		'''
		A function called in more than one location. Gets the last entry in the self.step_back_cache and harnesses
		the relevant parameters from it, then clears the EMBoxerModule of relevant boxes, and then an autobox is
		forced. Making the autoboxing sensitive to the self.auto_update parameter would make it messy and tricky to handle.
		'''
		if len(self.step_back_cache) == 0: raise RuntimeError("can't proceed there are no entries in the step_back cache")
		self.target().clear_boxes([SwarmBoxer.REF_NAME,SwarmBoxer.AUTO_NAME,SwarmBoxer.WEAK_REF_NAME])
#		self.debug_back("hb a")
		self.load_from_list(deepcopy(self.step_back_cache[-1]))
		boxes = [ [box.x, box.y, box.type_name(), box.peak_score] for box in self.ref_boxes if box.image_name == self.current_file ]
#		self.debug_back("hb b")
		self.target().add_boxes(boxes)
		self.target().get_2d_window().updateGL()
		if self.templates != None:
			self.auto_box(self.target().current_file(),parameter_update=False,cache=False)
		else:
			print "handle the case of no templates ?"
			
	def step_forward(self):
		'''
		Manages the case when the user has clicked "Step Forward" in the SwarmPanel
		In this case the last entry in self.step_fwd_cache is used to set the states of 
		the relevant variable attributes of this object. After this we have to clear the
		EMBoxerModule and redo autoboxing. Note that I made this function force an autobox,
		simply because the it would get messy otherwise.
		Handles any necessary updates of the SwarmPanel
		'''
		if len(self.step_fwd_cache) == 0: raise RuntimeError("Step forward cache has no entries")
		l = self.step_fwd_cache.pop(-1)
		
		if len(self.step_fwd_cache) == 0: self.panel_object.enable_step_forward(False)
		else: self.panel_object.enable_step_forward(True,len(self.step_fwd_cache)) # solely for the tooltip
		
		self.panel_object.enable_step_back(True,len(self.step_back_cache))
		self.step_back_cache.append(l)

		self.target().clear_boxes([SwarmBoxer.REF_NAME,SwarmBoxer.AUTO_NAME,SwarmBoxer.WEAK_REF_NAME])
		self.load_from_list(deepcopy(self.step_back_cache[-1]))
		boxes = [ [box.x, box.y, box.type_name(), box.peak_score] for box in self.ref_boxes if box.image_name == self.current_file]
		self.target().add_boxes(boxes)
		self.target().get_2d_window().updateGL()
		if len(self.ref_boxes) > 0:
			self.auto_box(self.target().current_file(),cache=False)
			
		self.panel_object.update_states(self)
		if self.template_viewer != None:
			self.template_viewer.set_data(self.templates,soft_delete=True)
			self.template_viewer.updateGL()
			
		if self.templates != None:
			self.panel_object.enable_view_template(True)
		
	def cache_current_state(self):
		'''
		Adds the current state to self.step_back_cache
		As a result resets self.step_fwd_cache (think in terms of undo and redo)
		Also updates the SwarmPanel
		'''
		self.step_back_cache.append(self.to_list())
		self.step_fwd_cache = []
		self.panel_object.enable_step_forward(False)
		self.panel_object.enable_step_back(True,len(self.step_back_cache))
		if len(self.step_back_cache) >= SwarmBoxer.CACHE_MAX: self.step_back_cache.pop(0)
		
	def cache_to_database(self):
		'''
		Stores the SwarmBoxer.SWARM_BOXERS and SwarmBoxer.SWARM_FWD_BOXER entries on the local database 
		'''
		set_database_entry(self.target().current_file(),SwarmBoxer.SWARM_BOXERS,self.step_back_cache)
		set_database_entry(self.target().current_file(),SwarmBoxer.SWARM_FWD_BOXERS,self.step_fwd_cache)
		
	def handle_file_change(self,file_name):
		'''
		Handles the situation when the user changes the current image being studied in the main interface
		in the EMBoxerModule.
		A groovy thing happens - if the user has "auto updates" selected in the SwarmPanel then
		the last boxer from the previous image (i.e. self.step_back_cache[-1]) is pushed to the top
		of the boxer stack for the new image and auto boxing occurs. This is easily undone if the results
		are unwanted, i.e. by pressing "Step Back" in the SwarmPanel
		
		A variety of basic things happen too. And cached boxer data are restored from the local database,
		allowing the user to step back and step forward (as in the buttons in the Swarm Panel), etc.
		
		'''
		l = None
		if self.auto_update and len(self.step_back_cache) > 0:
			l = deepcopy(self.step_back_cache[-1])
		
		self.mvt_cache = get_database_entry(file_name,SwarmBoxer.SWARM_USER_MVT,dfl=[])
		
		self.step_fwd_cache = get_database_entry(file_name,SwarmBoxer.SWARM_FWD_BOXERS,dfl=[])
		if len(self.step_fwd_cache) > 0: self.panel_object.enable_step_forward(True,len(self.step_fwd_cache))
		else: self.panel_object.enable_step_forward(False)
			
		self.step_back_cache = get_database_entry(file_name,SwarmBoxer.SWARM_BOXERS,dfl=[])
		
		if len(self.step_back_cache) > 0 and l != None:
			print self.step_back_cache[-1][10],l[10]
			if self.step_back_cache[-1][10] == l[10]:
				print "saved a redundant step"
				l = None
	
		if l != None:
			self.step_back_cache.append(l)
			self.cache_to_database()

		if len(self.step_back_cache) > 0: self.panel_object.enable_step_back(True,len(self.step_back_cache))
		else: self.panel_object.enable_step_back(False)
		
		if l != None:
			self.load_from_last_state()
		else:
			if len(self.step_back_cache): self.load_from_list(deepcopy(self.step_back_cache[-1]))

		self.panel_object.update_states(self)
		if self.template_viewer != None:
			self.template_viewer.set_data(self.templates,soft_delete=True)
			self.template_viewer.updateGL()
	
		if self.templates != None:
			self.panel_object.enable_view_template(True)
	
	def set_interactive_threshold(self,val):
		'''
		The SwarmPanel calls this function when the user changes the interactive threshold
		@param val the new interactive threshold to set
		'''
		if self.interactive_threshold == val: return
		
		self.interactive_threshold = val
		if self.auto_update and self.templates != None:
			self.auto_box(self.target().current_file(), parameter_update=True, force_remove_auto_boxes=True)
		elif not self.auto_update:
				self.panel_object.enable_auto_box(True)
	
	def disable_interactive_threshold(self):
		'''
		The SwarmPanel calls this function when the user clicks to disable the interactive threshold
		'''
		self.interactive_threshold = None
		if self.auto_update and self.templates != None:
			self.auto_box(self.target().current_file(), parameter_update=True, force_remove_auto_boxes=True)
		elif not self.auto_update:
			self.panel_object.enable_auto_box(True)
			
	def view_template_clicked(self):
		'''
		The SwarmPanel calls this function.
		Loads an EMImageMXModule for viewing (if it doesn't already exist)
		Brings the template viewer to the foreground
		'''
		if self.template_viewer == None:
			from emimagemx import EMImageMXModule
			self.template_viewer = EMImageMXModule()
			self.template_viewer.desktop_hint = "rotor" # this is to make it work in the desktop
				
			self.template_viewer.set_data(self.templates,soft_delete=True) # should work if self.templates is None
			self.template_viewer.update_window_title("Templates")
			from PyQt4 import QtCore
			QtCore.QObject.connect(self.template_viewer.emitter(),QtCore.SIGNAL("module_closed"),self.template_viewer_closed)
			
		get_application().show_specific(self.template_viewer)
		
	def template_viewer_closed(self):
		'''
		A slot for the module_closed signal from self.template_viewer
		'''
		self.template_viewer = None
		
	def set_update_template(self,val):
		'''
		Whether or not the act of adding a reference should for an update of the template
		@param val a boolena
		'''
		self.update_template = val
	
	def set_auto_update(self,val):
		'''
		Whether or not picked boxes should be updated when parameters are changed
		@param val a boolean 
		'''
		self.auto_update = val
	
	def set_particle_diameter(self,diameter):
		'''
		set the particle diameter, which should be an int
		@param diameter the approximate diameter of the particle
		'''
		if diameter != self.particle_diameter:
			self.particle_diameter = diameter
			self.signal_template_update = True
			if self.auto_update and self.templates != None: self.auto_box(self.target().current_file())
			elif not self.auto_update: self.panel_object.enable_auto_box(True)
		
	def set_pick_mode(self,mode):
		'''
		Sets self.pick_mode
		@param mode should be in SwarmBoxer.THRESHOLD, SwarmBoxer.SELECTIVE, SwarmBoxer.MORESELECTIVE 
		'''
		if mode not in [SwarmBoxer.THRESHOLD, SwarmBoxer.SELECTIVE, SwarmBoxer.MORESELECTIVE ]: raise RuntimeError("%s is an unknown SwarmBoxer mode" %mode)
		if mode != self.pick_mode:
			self.pick_mode = mode
			if self.auto_update and self.templates != None:
				self.auto_box(self.target().current_file(), parameter_update=False, force_remove_auto_boxes=True)
			elif not self.auto_update:
				self.panel_object.enable_auto_box(True)
	
	def move_auto_box(self,box_number,image_name,dx,dy):
		'''
		This is the solution to a conundrum - what if the user moves an auto box (a green one) but then reboxes, subsequently
		losing this "centering" metadata? The solution implemented here is to store the movement metadata and perform collision
		detection whenever autoboxing happens again.
		
		Here we update the "movement cache" to reflect the new metadata
		@param box_number the index corresponding to the stored box of the EMBoxList in the EMBoxerModule
		@param image_name the name of the image we're currently operating on - this is important because its used to store data in the local database
		@param dx the movement in the x direction (float)
		@param dy the movement in the y direction
		'''
		box = self.target().get_box(box_number)
		for i,[old,new] in enumerate(self.mvt_cache):
			dist = (new[0]-box.x)**2 + (new[1]-box.y)**2
			if dist < SwarmBoxer.MVT_THRESHOLD:
				self.mvt_cache[i][1] = [box.x+dx,box.y+dy]
				break
		else:
			self.mvt_cache.append([[box.x,box.y],[box.x+dx,box.y+dy]])
		
		set_database_entry(image_name,SwarmBoxer.SWARM_USER_MVT,self.mvt_cache)
		self.target().move_box(box_number,dx,dy)
		
	
	def update_auto_box_user_mvt(self,boxes):
		'''
		This is the solution to a conundrum - what if the user moves an auto box (a green one) but then reboxes, subsequently
		losing this "centering" metadata? The solution implemented here is to store the movement metadata and perform collision
		detection whenever autoboxing happens again.
		@param boxes a list of lists box data e.g. [[x,y,type,score],[x,y,type,score],....[int,int,str,float])  
		'''
		for box in boxes:
			for i,[old,new] in enumerate(self.mvt_cache):
				dist = (old[0]-box[0])**2 + (old[1]-box[1])**2
				if dist < SwarmBoxer.MVT_THRESHOLD:
					box[0] = new[0]
					box[1] = new[1]
	
	def move_ref(self,box_number,image_name,dx,dy,set_moved=True):
		'''
		Moves the reference stored internally and updates the EMBoxerModule so that it displays and stores the exact same thing.
		Separating what this object stores from what the EMBoxerModule stores decouple them and disentangles the overall design,
		but also makes some tasks 'fiddly'.
		
		This function takes care of telling the EMBoxerModule to correct what it's displaying - so the calling function should not.
		
		@param box_number the index corresponding to the stored box of the EMBoxList in the EMBoxerModule
		@param image_name the name of the image we're currently operating on
		@param dx the movement in the x direction (float)
		@param dy the movement in the y direction 
		@param set_moved a boolean indicating whether the SwarmBox.ever_moved attribute should be set to True. Search for ever_moved to see where it's used
		'''
		box = self.target().get_box(box_number)
		for i,rbox in enumerate(self.ref_boxes):
			if rbox.x == box.x and rbox.y == box.y and rbox.image_name == image_name:
				rbox.x += dx
				rbox.y += dy
				if set_moved:rbox.ever_moved = True
				new_box = EMBox(rbox.x,rbox.y,rbox.type_name(),rbox.peak_score)
				self.target().set_box(new_box,box_number,update_display=True)
				break
		else:
			raise RuntimeError("Attempt to move a reference failed")
		
	def remove_ref(self,box,image_name):
		'''
		Remove the reference, i.e. in response to a mouse delete event
		
		Does not tell the EMBoxModule to removed the displayed box - the calling function should do that.
		
		@param box an EMBox, as returned by the call to EMBoxerModule.get_box
		@param image_name the name of the image we're operating on
		'''
		for i,rbox in enumerate(self.ref_boxes):
			if rbox.x == box.x and rbox.y == box.y and rbox.image_name == image_name:
				b = self.ref_boxes.pop(i)
				if self.auto_update:
					if len(self.ref_boxes) > 0:
						if box.type == SwarmBoxer.REF_NAME:
							self.signal_template_update=True 
						self.auto_box(image_name,force_remove_auto_boxes=True)
					else:
						self.clear_all()
				else:
					self.panel_object.enable_auto_box(True)
				break
		else:
			raise RuntimeError("Attempt to remove a reference failed")
					
	
	def add_ref(self,x,y,image_name):
		'''
		Add a reference at the given coordinate and from the given image
		
		Does not tell the EMBoxerModule to add the box - the calling function must do this
		
		@param x the x coordinate of the box
		@param y the y coordinate of the box
		@parm image_name the name of the image we're operating on
		'''
		new_box = SwarmBox(x,y,image_name,self.update_template)
		self.ref_boxes.append(new_box)
		if self.update_template: 
			self.signal_template_update = True
			box_num = self.target().add_box(x,y,type=SwarmBoxer.REF_NAME)
		else:
			box_num = self.target().add_box(x,y,type=SwarmBoxer.WEAK_REF_NAME)
				
		self.get_2d_window().updateGL()
		
		return box_num
		
		
	def ref_released(self,image_name):
		'''
		This function called when a reference box is released, i.e. by the mouse
		This can cause an autoboxing update if the self.auto_update parameter is true
		@param image_name the name of the image that is being operated on 
		'''
		if self.auto_update:
			self.auto_box(image_name)
		else:
			self.panel_object.enable_auto_box(True)
		#DONT THINK THIS IS ADVISABLE...WALKING A FINE LINE
#		else:
#			self.cache_current_state()
#			self.cache_to_database()
			
#			
#	def try_to_center_ref(self,box_num):
#		if self.templates:
#			shrink = self.get_subsample_rate()
#			scaled_template = self.templates[-1].process("math.transform.scale",{"scale":shrink,"clip":self.particle_diameter})
#			scaled_template.process_inplace("xform.centeracf")
#			box = self.target().get_box(box_num)
#			dx,dy = self.xform_center_propagate([box.x,box.y],self.target().current_file(),scaled_template,self.particle_diameter)
#			print dx,dy,"try"
#			self.move_ref(box_num,self.target().current_file(),dx,dy)
#				
			
	def get_subsample_rate(self):
		'''
		Get the subsample rate advised by the SwarmBoxer, as based on self.particle_diameter and SWARM_TEMPLATE_MIN
		'''
		return int(math.ceil(float(self.particle_diameter)/float(SWARM_TEMPLATE_MIN)))
	
	def auto_box_clicked(self):
		'''
		When the autobox button is clicked then we force an autobox.
		'''
		self.auto_box(self.target().current_file(),force_remove_auto_boxes=True)	
	
	def auto_box(self,image_name,parameter_update=True,force_remove_auto_boxes=False,cache=True):
		'''
		The main autoboxing function, this has a lot in it but it's not that complicated
		@param image_name the image that we're boxing
		@param parameter_update, should generally be True,but may be False if the current parameters are known to be current (see self.load_from_last_state) 
		@param force_remove_auto_boxes if True all of the autoboxed boxes in the EMBoxerModule are removed and the 'entire' image is autoboxed again. This might be False if you know the template has not changed
		@param cache whether or not the newly establish state, i.e. at the end of this function, should be cached to the database and internally. Generally True but sometimes False (see self.load_from_last_state) .
		'''
		if self.signal_template_update or force_remove_auto_boxes:
			self.target().clear_boxes([SwarmBoxer.AUTO_NAME])
			self.get_2d_window().updateGL()
			
		
		if self.signal_template_update:
			self.templates = gen_rot_ave_template(image_name,self.ref_boxes,self.get_subsample_rate(),self.particle_diameter)
			self.panel_object.enable_view_template(True)
			self.signal_template_update = False
			if self.template_viewer != None:
				self.template_viewer.set_data(self.templates,soft_delete=True)
				self.template_viewer.updateGL()
				
		shrink = self.get_subsample_rate()

		
		exclusion_image = self.target().get_exclusion_image(mark_boxes=True)
		
		mediator = SwarmFLCFImageMediator(self.particle_diameter/(shrink*2),shrink,self.templates[-1])
		correlation_image = FLCFImageCache.get_image(image_name,mediator)
		
		exclusion_shrink = exclusion_image.get_attr("shrink")
		
		if shrink != exclusion_shrink: 
			# the amount by which the exclusion is shrunken does not match the amount by which the SwarmBoxer shrinks - so we have to scale
			# to do: test this
			#print "shrink changed does this work?",shrink,exclusion_shrink,self.particle_diameter, SWARM_TEMPLATE_MIN,TEMPLATE_MIN
			rescale = float(exclusion_shrink)/shrink
			oldx = exclusion_image.get_xsize()
			oldy = exclusion_image.get_ysize()
			newx = correlation_image.get_xsize()
			newy = correlation_image.get_ysize()
			r = Region((oldx-newx)/2,(oldy-newy)/2,newx,newy)
			t = Transform()
			t.set_scale(rescale)
			if rescale > 1.0:
				exclusion_image.clip_inplace(r)
				exclusion_image.transform(t)
			else:
				exclusion_image.transform(t)
				exclusion_image.clip_inplace(r)
				
		for box in self.ref_boxes:
			box.update_picking_data(mediator)
			

		if parameter_update:
			if not self.update_opt_picking_data(): 
				print "funny error"
				return 
		
		if self.pick_mode == SwarmBoxer.THRESHOLD: mode = 0
		elif self.pick_mode == SwarmBoxer.SELECTIVE: mode = 1
		elif self.pick_mode == SwarmBoxer.MORESELECTIVE: mode = 2
		
		searchradius = self.templates[-1].get_xsize()/2
		correlation = FLCFImageCache.get_image(image_name,mediator)
		soln = BoxingTools.auto_correlation_pick(correlation,self.peak_score,searchradius,self.profile,exclusion_image,self.profile_trough_point,mode)
		
		scaled_template = self.templates[-1].process("math.transform.scale",{"scale":shrink,"clip":self.particle_diameter})
		scaled_template.process_inplace("xform.centeracf")
		boxes = []
		for b in soln:
			x = b[0]
			y = b[1]
			xx = int(x*shrink)
			yy = int(y*shrink)
			type = SwarmBoxer.AUTO_NAME
			peak_score = correlation.get(x,y)
			box = [xx,yy,type,peak_score]
			self.center_propagate(box,image_name,scaled_template,self.particle_diameter)
			boxes.append(box)
		
		
		self.update_auto_box_user_mvt(boxes)
		
		for box in self.ref_boxes:
			if not box.ever_moved and box.image_name == self.target().current_file():
				box_num = self.target().detect_box_collision([box.x,box.y])
				if box_num == -1: raise RuntimeError("could not find reference")
				else:
					box = self.target().get_box(box_num)
					if box.type not in [SwarmBoxer.REF_NAME,SwarmBoxer.WEAK_REF_NAME]:
						raise RuntimeError("Did not get a reference when doing collision detection")
					
					dx,dy = self.xform_center_propagate([box.x,box.y],image_name,scaled_template,self.particle_diameter)
					self.move_ref(box_num,image_name,dx,dy)
		
	   	boxes.sort(compare_box_correlation) # sorting like this will often put large ice contaminations in a group, thanks Pawel Penczek
		self.target().add_boxes(boxes)
		
		if cache:
			self.cache_current_state()
			self.cache_to_database()
			
		self.panel_object.enable_auto_box(False)
	
	def update_opt_picking_data(self):
		'''
		This is the function that decides on the picking parameters of the SwarmBoxer, based on the reference
		boxes stored in self.ref_boxes
		'''
		self.profile = None
		self.peak_score = None
		self.profile_trough_point = None
		
		for box in self.ref_boxes:
			if self.interactive_threshold != None: 
				self.peak_score = self.interactive_threshold
			else:
				if box.peak_score == None: continue
				
				if self.peak_score == None or box.peak_score < self.peak_score:
					self.peak_score = box.peak_score
		
			if self.profile == None: self.profile = deepcopy(box.profile)  # or else I'd alter it and muck everything up
			else:
				if len(self.profile) != len(box.profile): raise RuntimeError("This should never happen")
				
				profile = box.profile
				for j in xrange(0,len(self.profile)):
					if profile[j] < self.profile[j]: self.profile[j] = profile[j]
		
		if self.profile == None:
			return False
		
		max_radius =  int(len(self.profile)*SwarmBoxer.PROFILE_MAX)
		tmp = self.profile[0]
		self.profile_trough_point = 0
		for i in range(1,max_radius):
			if self.profile[i] > tmp and tmp > 0:
				tmp = self.profile[i]
				self.profile_trough_point = i
				
		self.panel_object.set_picking_data(self.peak_score, self.profile, self.profile_trough_point)
		
		return True
	
	def clear_all(self):
		'''
		Clears all associated boxes from the EMBoxerModule and internally, establishing a clean, blank state
		'''
		self.target().clear_boxes([SwarmBoxer.REF_NAME,SwarmBoxer.AUTO_NAME,SwarmBoxer.WEAK_REF_NAME])
		self.reset()
		self.panel_object.enable_view_template(False)
		self.panel_object.enable_auto_box(False)
		if self.template_viewer != None: self.template_viewer.set_data(None)
		self.cache_current_state()
		self.cache_to_database()
		
		
	def center_propagate(self,box,image_name,template,box_size):
		'''
		Centers the box argument in place
		@param box a list like [x,y,type,float] - only x and y are used
		@param image_name the name of the image we're operating on
		@param template the template correctly scaled to the have the same angstrom per pixel as the image (named image_name) stored on disk
		@param box_size the size of the box used to center - see xform_center_propagate
		'''
		dx,dy = self.xform_center_propagate(box,image_name,template,box_size)
		box[0] += dx
		box[1] += dy

#		
	def xform_center_propagate(self,box,image_name,template,box_size):
		'''
		Centers a box that was generated in a shrunken image by getting the 'real particle' out of the large
		image on disk and doing a ccf with the template - then I just find the peak and use that to center
		@param box a list like [x,y,type,float] - only x and y are used
		@param image_name the name of the image we're operating on
		@param template the template correctly scaled to the have the same angstrom per pixel as the image (named image_name) stored on disk
		@param box_size the size of the box used to center
		Returns the dx and dy parameters, i.e. does not actually alter the box
		'''
	  	global BigImageCache
	  	image = BigImageCache.get_image_directly(image_name)
			 
		xc = box[0]-box_size/2
		yc = box[1]-box_size/2
		r = Region(xc,yc,box_size,box_size)
		particle = image.get_clip(r)
		ccf  = particle.calc_ccf(template)
		trans = ccf.calc_max_location_wrap(particle.get_xsize()/2,particle.get_ysize()/2,0)
		dx = trans[0]
		dy = trans[1]
		return dx,dy
		
					
class SwarmTool(SwarmBoxer):
	'''
	A class that knows how to handle mouse erase events for a GUIBox
	'''	
	
	def __init__(self,target,particle_diameter=128):
		SwarmBoxer.__init__(self,particle_diameter)
		self.target = weakref.ref(target)
		self.panel_object = SwarmPanel(self,self.particle_diameter)
		self.current_file = None # the name of the file that is being studied in the main viewer
		self.moving_box = None # keeps track of the moving box, will be a list in the format [[int,int],int,str] = [[x,y],box_number,box_type]
			
	def unique_name(self): return "Swarm"
	
	def get_widget(self):
		if self.panel_object == None:
			self.panel_object = SwarmPanel(self,self.particle_diameter)
		return self.panel_object.get_widget()
	
	def icon(self):
		from PyQt4 import QtGui
		return QtGui.QIcon(get_image_directory() + "swarm_icon.png")
	
		
	def set_current_file(self,file_name):
		'''
		If the behavior of this Handler does not if the file changes, but the function needs to be supplied 
		'''
		if self.current_file != file_name:
			self.current_file = file_name
			self.handle_file_change(file_name)
			
	
	def get_2d_window(self): return self.target().get_2d_window()
	
	def mouse_move(self,event):
		pass
		
	def mouse_wheel(self,event):
		pass
	def mouse_down(self,event):
		m = self.get_2d_window().scr_to_img((event.x(),event.y()))
		box_num = self.target().detect_box_collision(m)
		box = self.target().get_box(box_num)
		from PyQt4.QtCore import Qt
		if box_num == -1:
			if event.modifiers()&Qt.ShiftModifier : return # the user tried to delete nothing
			box_num = self.add_ref(m[0],m[1],self.target().current_file())
			b = self.target().get_box(box_num)
			self.moving=[m,box_num,b.type]
		else:
			if box.type in [SwarmBoxer.REF_NAME,SwarmBoxer.AUTO_NAME,SwarmBoxer.WEAK_REF_NAME]:
				from PyQt4.QtCore import Qt
				if event.modifiers()&Qt.ShiftModifier :
					self.handle_box_delete(box,box_num)
				else:
					# if we make it here than the we're moving a box
					self.moving=[m,box_num,box.type]
					self.target().moving_box_established(box_num)
			else:
				print 'should change mouse handler now'
			
	
	def handle_box_delete(self,box,box_num):
		if box.type == SwarmBoxer.AUTO_NAME:
			self.target().remove_box(box_num,exclude_region=True)
		elif box.type == SwarmBoxer.REF_NAME or box.type == SwarmBoxer.WEAK_REF_NAME:
			self.target().remove_box(box_num)
			self.remove_ref(box,self.target().current_file())
		else:
			raise RuntimeError("%s is an unkown box type" %box.type)
	
	def mouse_drag(self,event) :
		m=self.get_2d_window().scr_to_img((event.x(),event.y()))
		from PyQt4.QtCore import Qt
		if event.modifiers()&Qt.ShiftModifier:
			box_num = self.target().detect_box_collision(m)
			box = self.target().get_box(box_num)
			if ( box_num != -1):
				if box.type in [SwarmBoxer.REF_NAME,SwarmBoxer.AUTO_NAME,SwarmBoxer.WEAK_REF_NAME]:
					self.handle_box_delete(box,box_num)			
		elif self.moving != None:
			oldm = self.moving[0]
			dx = m[0]-oldm[0]
			dy = m[1]-oldm[1]

			if self.moving[2] in [SwarmBoxer.REF_NAME,SwarmBoxer.WEAK_REF_NAME]:
				self.move_ref(self.moving[1],self.target().current_file(),dx,dy)
			else:
				self.move_auto_box(self.moving[1],self.target().current_file(),dx,dy)
				
			self.moving[0] = m
	def mouse_up(self,event) :
		if self.moving != None:
			self.target().box_released(self.moving[1])
		
		if self.moving[2] in [SwarmBoxer.REF_NAME,SwarmBoxer.WEAK_REF_NAME]:
			self.ref_released(self.target().current_file())
			
		self.moving= None
	

if __name__ == "__main__":
	main()
