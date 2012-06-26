#!/usr/bin/env python
#
# Author: 
# Copyright (c) 2012 The University of Texas - Houston Medical School
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#
#

import	global_def
from	global_def 	import *
from	optparse 	import OptionParser
from	EMAN2 		import EMUtil
import	os
import	sys
from 	time		import	time

t0 = time()

def main():

	def params_3D_2D_NEW(phi, theta, psi, s2x, s2y, mirror):
		if mirror:
			m = 1
			alpha, sx, sy, scalen = compose_transform2(0, s2x, s2y, 1.0, 540.0-psi, 0, 0, 1.0)
		else:
			m = 0
			alpha, sx, sy, scalen = compose_transform2(0, s2x, s2y, 1.0, 360.0-psi, 0, 0, 1.0)
		return  alpha, sx, sy, m
	
	progname = os.path.basename(sys.argv[0])
	usage = progname + " prj_stack volume --iter --var --sym=symmetry --MPI"
	parser = OptionParser(usage, version=SPARXVERSION)

	parser.add_option("--radius", 		type="int"         ,	default=-1   ,				help="radius of region in concern" )
	parser.add_option("--iter", 		type="int"         ,	default=40   ,				help="maximum number of iterations (stop criterion of reconstruction process)" )
	parser.add_option("--abs", 			type="float"       ,	default=0.0  ,				help="minimum average absolute change of voxels' values (stop criterion of reconstruction process)" )
	parser.add_option("--squ", 			type="float"       ,	default=0.0  ,				help="minimum average squared change of voxels' values (stop criterion of reconstruction process)" )
	parser.add_option("--sym" , 		type="string"      ,	default="c1" ,				help="symmetry")
	parser.add_option("--VAR" , 		action="store_true",	default=False,				help="stack on input consists of variances")
	parser.add_option("--SND",			action="store_true",	default=False,				help="compute squared normalized differences")
	parser.add_option("--CTF",			action="store_true",	default=False,				help="use CFT correction")
	parser.add_option("--VERBOSE",		action="store_true",	default=False,				help="comments")
	parser.add_option("--img_per_grp",	type="int"         ,	default=10   ,				help="number of neighbouring projections")
	parser.add_option("--nvec",			type="int"         ,	default=0    ,				help="number of eigenvectors, default = 0 meaning no PCA calculated")
	parser.add_option("--npad",			type="int"         ,	default=2    ,				help="number of time to pad the original images")
	parser.add_option("--freq",			type="float"       ,	default=0.0  ,				help="stop-band frequency")
	parser.add_option("--fall_off",		type="float"       ,	default=0.0  ,				help="fall off of the filter")
	parser.add_option("--ave2D",		type="string"	   ,	default=False,				help="write to the disk a stack of 2D averages")
	parser.add_option("--var2D",		type="string"	   ,	default=False,				help="write to the disk a stack of 2D variances")
	parser.add_option("--ave3D",		type="string"	   ,	default=False,				help="write to the disk reconstructed 3D average")
	parser.add_option("--var3D",		type="string"	   ,	default=False,				help="compute 3D variance (time consuming!)")
	parser.add_option("--no_norm",		action="store_true",	default=False,				help="do not use normalization")
	parser.add_option("--MPI" , 		action="store_true",	default=False,				help="use MPI version")

	(options,args) = parser.parse_args()
	
	from mpi import mpi_init, mpi_comm_rank, mpi_comm_size, MPI_COMM_WORLD
	from mpi import mpi_barrier, mpi_reduce, mpi_bcast, MPI_FLOAT, MPI_SUM, MPI_INT, MPI_MAX
	from applications import MPI_start_end
	from reconstruction import recons3d_em, recons3d_em_MPI
	from reconstruction	import recons3d_4nn_MPI, recons3d_4nn_ctf_MPI
	from utilities import print_begin_msg, print_end_msg, print_msg
	from utilities import read_text_row, get_image
	from utilities import bcast_EMData_to_all, bcast_number_to_all

	sys.argv = mpi_init(len(sys.argv), sys.argv)
	myid = mpi_comm_rank(MPI_COMM_WORLD)
	number_of_proc = mpi_comm_size(MPI_COMM_WORLD)
	main_node = 0

	if len(args) == 2:
		stack = args[0]
		vol_stack = args[1]
	else:
		ERROR("incomplete list of arguments", "sxvariances3d", 1)
		exit()
	if not options.MPI:
		ERROR("Non-MPI not supported!", "sx3Dvariance", myid=myid)
		exit()
	if options.VAR and options.SND:
		ERROR("Only one of var and SND can be set!", "sx3Dvariance", myid=myid)
		exit()
	if options.VAR and (options.ave2D or options.ave3D or options.var2D): 
		ERROR("When VAR is set, the program cannot output ave2D, ave3D or var2D", "sx3Dvariance", myid=myid)
		exit()
	if options.SND and (options.ave2D or options.ave3D):
		ERROR("When SND is set, the program cannot output ave2D or ave3D", "sx3Dvariance", myid=myid)
		exit()
	if options.nvec > 0 and options.ave3D == None:
		ERROR("When doing PCA analysis, one must set ave3D", "sx3Dvariance", myid=myid)
		exit()
		 

	if global_def.CACHE_DISABLE:
		from utilities import disable_bdb_cache
		disable_bdb_cache()
	global_def.BATCH = True

	if myid == main_node:
		print_begin_msg("sx3Dvariance")
		print_msg("%-70s:  %s\n"%("Input stack", stack))
	
	img_per_grp = options.img_per_grp
	nvec = options.nvec
	radius = options.radius

	if myid == main_node:
		nima = EMUtil.get_image_count(stack)
		img = get_image(stack)
		nx = img.get_xsize()
		ny = img.get_ysize()
	else:
		nima = 0
		nx = 0
		ny = 0
	nima = bcast_number_to_all(nima)
	nx = bcast_number_to_all(nx)
	ny = bcast_number_to_all(ny)
	if radius == -1: radius = nx/2-2

	if myid == main_node:
		print_msg("%-70s:  %d\n"%("Number of projection", nima))
		print_msg("%-70s:  %d\n"%("nx", nx))
		print_msg("%-70s:  %d\n"%("ny", ny))
		if options.VERBOSE:  print "Number of projections:", nima
		
	img_begin, img_end = MPI_start_end(nima, number_of_proc, myid)

	if options.SND:
		from projection		import prep_vol, prgs
		from statistics		import im_diff
		from utilities		import get_im, model_circle, get_params_proj, set_params_proj
		from utilities		import get_ctf, generate_ctf
		from filter			import filt_ctf
		
		imgdata = EMData.read_images(stack, range(img_begin, img_end))

		if options.CTF:
			vol = recons3d_4nn_ctf_MPI(myid, imgdata, 1.0, symmetry=options.sym, npad=options.npad, xysize=-1, zsize=-1)
		else:
			vol = recons3d_4nn_MPI(myid, imgdata, symmetry=options.sym, npad=options.npad, xysize=-1, zsize=-1)
	
		bcast_EMData_to_all(vol, myid)
		volft, kb = prep_vol(vol)

		mask = model_circle(nx/2-2, nx, ny)
		varList = []
		for i in xrange(img_begin, img_end):
			phi, theta, psi, s2x, s2y = get_params_proj(imgdata[i-img_begin])
			ref_prj = prgs(volft, kb, [phi, theta, psi, -s2x, -s2y])
			if options.CTF:
				ctf_params = get_ctf(imgdata[i-img_begin])
				ref_prj = filt_ctf(ref_prj, generate_ctf(ctf_params))
			diff, A, B = im_diff(ref_prj, imgdata[i-img_begin], mask)
			diff2 = diff*diff
			set_params_proj(diff2, [phi, theta, psi, s2x, s2y])
			varList.append(diff2)
		mpi_barrier(MPI_COMM_WORLD)
	elif options.VAR:
		varList = EMData.read_images(stack, range(img_begin, img_end))
	else:
		from utilities		import bcast_number_to_all, bcast_list_to_all, send_EMData, recv_EMData
		from utilities		import set_params_proj, get_params_proj, params_3D_2D, get_params2D, set_params2D, compose_transform2
		from utilities		import model_blank, nearest_proj, model_circle
		from applications	import pca
		from statistics		import avgvar, avgvar_ctf, ccc
		from filter		import filt_tanl
		from morphology		import threshold
		from projection 	import project
		from sets		import Set			

		if myid == main_node:
			t1 = time()
			proj_angles = []
			aveList = []
			tab = EMUtil.get_all_attributes(stack, 'xform.projection')
			for i in xrange(nima):
				t = tab[i].get_params('spider')
				phi = t['phi']
				theta = t['theta']
				psi = t['psi']
				x = theta
				if x > 90.0: x = 180.0 - x
				x = x*10000+psi
				proj_angles.append([x, t['phi'], t['theta'], t['psi'], i])
			t2 = time()
			print_msg("%-70s:  %d\n"%("Number of neighboring projections", img_per_grp))
			print_msg("...... Finding neighboring projections\n")
			if options.VERBOSE:
				print "Number of images per group: ", img_per_grp	
				print "Now grouping projections"				
			proj_angles.sort()

		proj_angles_list = [0.0]*(nima*4)
		if myid == main_node:
			for i in xrange(nima):
				proj_angles_list[i*4] = proj_angles[i][1] 
				proj_angles_list[i*4+1] = proj_angles[i][2] 
				proj_angles_list[i*4+2] = proj_angles[i][3] 
				proj_angles_list[i*4+3] = proj_angles[i][4]
		proj_angles_list = bcast_list_to_all(proj_angles_list)
		proj_angles = []
		for i in xrange(nima):
			proj_angles.append([proj_angles_list[i*4], proj_angles_list[i*4+1], proj_angles_list[i*4+2], int(proj_angles_list[i*4+3])])
		del proj_angles_list

		proj_list, mirror_list = nearest_proj(proj_angles, img_per_grp, range(img_begin, img_end))

		all_proj = Set()
		for im in proj_list:
			for jm in im:
				all_proj.add(proj_angles[jm][3])

		all_proj = list(all_proj)
		if options.VERBOSE:
			print "One node %2d, number of images need to read = %5d"%(myid, len(all_proj))
		
		index = {}
		for i in xrange(len(all_proj)): index[all_proj[i]] = i
		mpi_barrier(MPI_COMM_WORLD)

		if myid == main_node:
			print_msg("%-70s:  %.2f\n"%("Finding neighboring projections lasted [s]", time()-t2))			
			print_msg("%-70s:  %d\n"%("Number of groups processed on main node", len(proj_list)))
			if options.VERBOSE:
				print "Grouping projections took: ", (time()-t2)/60	, "[min]"
				print "Number of groups on main node: ", len(proj_list)
		mpi_barrier(MPI_COMM_WORLD)

		if myid == main_node:
			print_msg("...... calculating the stack of 2D variances \n")
			if options.VERBOSE:
				print "Now calculating a stack of 2D variances"

		proj_params = [0.0]*(nima*5)
		aveList = []
		varList = []				
		if nvec > 0:
			eigList = [[] for i in xrange(nvec)]
		
		if options.VERBOSE: 	print "Begin to read images on processor %d"%(myid)
		ttt = time()
		imgdata = EMData.read_images(stack, all_proj)
		if options.VERBOSE:
			print "Reading images on processor %d done, time = %.2f"%(myid, time()-ttt)
			print "One processor %d, we got %d images"%(myid, len(imgdata))
		mpi_barrier(MPI_COMM_WORLD)
		
		'''	
		imgdata2 = EMData.read_images(stack, range(img_begin, img_end))
		if options.freq > 0.0:
			for k in xrange(len(imgdata2)):
				imgdata2[k] = filt_tanl(imgdata2[k], options.freq, options.fall_off)
		if options.CTF:
			vol = recons3d_4nn_ctf_MPI(myid, imgdata2, 1.0, symmetry=options.sym, npad=options.npad, xysize=-1, zsize=-1)
		else:
			vol = recons3d_4nn_MPI(myid, imgdata2, symmetry=options.sym, npad=options.npad, xysize=-1, zsize=-1)
		if myid == main_node:
			vol.write_image("vol_ctf.hdf")
			print_msg("Writing to the disk volume reconstructed from averages as		:  %s\n"%("vol_ctf.hdf"))
		del vol, imgdata2
		mpi_barrier(MPI_COMM_WORLD)
		'''
		from applications import prepare_2d_forPCA
		from utilities import model_blank		
		for i in xrange(len(proj_list)): 
			mi = index[proj_angles[proj_list[i][0]][3]]
			phiM, thetaM, psiM, s2xM, s2yM = get_params_proj(imgdata[mi])

			grp_imgdata = []
			for j in xrange(img_per_grp):
				mj = index[proj_angles[proj_list[i][j]][3]]
				phi, theta, psi, s2x, s2y = get_params_proj(imgdata[mj])
				alpha, sx, sy, mirror = params_3D_2D_NEW(phi, theta, psi, s2x, s2y, mirror_list[i][j])
				if thetaM <= 90:
					if mirror == 0:  alpha, sx, sy, scale = compose_transform2(alpha, sx, sy, 1.0, phiM-phi, 0.0, 0.0, 1.0)
					else:            alpha, sx, sy, scale = compose_transform2(alpha, sx, sy, 1.0, 180-(phiM-phi), 0.0, 0.0, 1.0)
				else:
					if mirror == 0:  alpha, sx, sy, scale = compose_transform2(alpha, sx, sy, 1.0, -(phiM-phi), 0.0, 0.0, 1.0)
					else:            alpha, sx, sy, scale = compose_transform2(alpha, sx, sy, 1.0, -(180-(phiM-phi)), 0.0, 0.0, 1.0)
				set_params2D(imgdata[mj], [alpha, sx, sy, mirror, 1.0])
				grp_imgdata.append(imgdata[mj])

			if not options.no_norm:
				mask = model_circle(nx/2-2, nx, nx)
				for k in xrange(img_per_grp):
					ave, std, minn, maxx = Util.infomask(grp_imgdata[k], mask, False)
					grp_imgdata[k] -= ave
					grp_imgdata[k] /= std
				del mask	

			if options.freq > 0.0:
				from utilities import pad
				from filter import filt_ctf
				from fundamentals import fft, window2d
				nx2 = 2*nx
				ny2 = 2*ny
				for k in xrange(img_per_grp):
					grp_imgdata[k] = window2d(fft( filt_tanl( filt_ctf(fft(pad(grp_imgdata[k], nx2, ny2, 1,0.0)), grp_imgdata[k].get_attr("ctf"), binary=1), options.freq, options.fall_off) ),nx,ny)
					#grp_imgdata[k] = filt_tanl(grp_imgdata[k], options.freq, options.fall_off)

			'''
			if i < 10 and myid == main_node:
				for k in xrange(10):
					grp_imgdata[k].write_image("grp%03d.hdf"%i, k)
			'''

			ave, grp_imgdata = prepare_2d_forPCA(grp_imgdata)
			var = model_blank(nx,ny)
			for q in grp_imgdata:  Util.add_img2( var, q )
			Util.mul_scalar( var, 1.0/(len(grp_imgdata)-1))
			#if options.CTF:	ave, var = avgvar_ctf(grp_imgdata, mode="a")
			#else:	            ave, var = avgvar(grp_imgdata, mode="a")

			var = threshold(var)
			set_params_proj(ave, [phiM, thetaM, 0.0, 0.0, 0.0])
			set_params_proj(var, [phiM, thetaM, 0.0, 0.0, 0.0])

			aveList.append(ave)
			varList.append(var)

			#rad = nx/2
			if options.VERBOSE:
				print "%5.2f%% done on processor %d"%(i*100.0/len(proj_list), myid)
			if nvec > 0:
				eig = pca(input_stacks=grp_imgdata, subavg=ave, mask_radius=radius, nvec=nvec, incore=True, shuffle=False, genbuf=True)
				for k in xrange(nvec):
					set_params_proj(eig[k], [phiM, thetaM, 0.0, 0.0, 0.0])
					eigList[k].append(eig[k])

		del imgdata
		#  All averages, variances, and eigenvectors are computed

		if options.ave2D:
			for i in xrange(number_of_proc):
				if myid == i:
					for im in xrange(len(aveList)):
						aveList[im].write_image(options.ave2D, im+img_begin)
				mpi_barrier(MPI_COMM_WORLD)

		if options.ave3D:
			if options.VERBOSE:
				print "Reconstructing 3D average volume"
			ave3D = recons3d_4nn_MPI(myid, aveList, symmetry=options.sym, npad=options.npad, xysize=-1, zsize=-1)
			bcast_EMData_to_all(ave3D, myid)
			if myid == main_node:
				ave3D.write_image(options.ave3D)
				print_msg("%-70s:  %s\n"%("Writing to the disk volume reconstructed from averages as", options.ave3D))
		del ave, var, proj_list, stack, phi, theta, psi, s2x, s2y, alpha, sx, sy, mirror, aveList

		if nvec > 0:

			if options.VERBOSE:
				print "Reconstruction eigenvolumes"
			for k in xrange(nvec):
				cont = True
				while(cont):
					eig3D = recons3d_4nn_MPI(myid, eigList[k], symmetry=options.sym, npad=options.npad, xysize=-1, zsize=-1)
					eig3D = filt_tanl(eig3D, options.freq, options.fall_off)*mask() ##################
					eig3Df,kb = prep_vol( eig3D )
					#c = [0.0]*len(eigList[k])
					cont = False
					for l in xrange(len(eigList[k])):
						phi, theta, psi, s2x, s2y = get_params_proj(eigList[k][l])
						proj = prgs(eig3Df, kb, [phi, theta, psi, s2x, s2y])
						cl = ccc(proj, eigList[k][l], mask##########)
						if( cl < 0.0 ):
							cont = True
							eigList[k][l] *= -1.0
					#  Gather cont and send back
					# gather all ccc's
					# decided what is the correct sign
					#  send information back
					#  correct sign of eigvecs
				
				
				
				
				if myid == main_node:
					eig3D.write_image("eig3d_%03d.hdf"%k)
				del eig3D
				mpi_barrier(MPI_COMM_WORLD)
			del eigList

		if options.ave3D: del ave3D

	if options.var2D:
		for i in xrange(number_of_proc):
			if myid == i:
				for im in xrange(len(varList)):
					varList[im].write_image(options.var2D, im+img_begin)
			mpi_barrier(MPI_COMM_WORLD)
	mpi_barrier(MPI_COMM_WORLD)

	if  options.var3D:
		if myid == main_node and options.VERBOSE:
			print "Reconstructing 3D variance volume"

		t6 = time()
		res = recons3d_em_MPI(varList, vol_stack, options.iter, radius, options.abs, True, options.sym, options.squ)
		if myid == main_node:
			res.write_image(vol_stack)

		if myid == main_node:
			print_msg("%-70s:  %.2f\n"%("Reconstructing 3D variance lasted [s]", time()-t6))
			if options.VERBOSE:
				print "Reconstruction took: %.2f [min]"%((time()-t6)/60)

		if myid == main_node:
			print_msg("%-70s:  %.2f\n"%("Total time for these computations [s]", time()-t0))
			if options.VERBOSE:
				print "Total time for these computations: %.2f [min]"%((time()-t0)/60)
			print_end_msg("sx3Dvariance")

	global_def.BATCH = False

	from mpi import mpi_finalize
	mpi_finalize()

if __name__=="__main__":
	main()
