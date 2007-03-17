/*
 * Author: Steven Ludtke, 04/10/2003 (sludtke@bcm.edu)
 * Copyright (c) 2000-2006 Baylor College of Medicine
 * 
 * This software is issued under a joint BSD/GNU license. You may use the
 * source code in this file under either license. However, note that the
 * complete EMAN2 and SPARX software packages have some GPL dependencies,
 * so you are responsible for compliance with the licenses of these packages
 * if you opt to use BSD licensing. The warranty disclaimer below holds
 * in either instance.
 * 
 * This complete copyright notice must be included in any revised version of the
 * source code. Additional authorship citations may be added, but existing
 * author citations must be preserved.
 * 
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 * 
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 * 
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
 * 
 * */

#define NO_IMPORT_ARRAY

#include <Python.h>
#include <boost/python/tuple.hpp>
#include "typeconverter.h"
#include "emdata.h"

using namespace EMAN;


python::numeric::array EMAN::make_numeric_array(float * data, vector<int> dims)
{
	size_t total = 1;
	vector<int>::iterator iter = dims.begin();
	while(iter != dims.end()){
		total *= *iter;
		++iter;
	}    

	python::object obj(python::handle<>(PyArray_FromDimsAndData(dims.size(),&dims[0],
																PyArray_FLOAT, (char*)data)));


	return python::extract<python::numeric::array>(obj);
}

python::numeric::array EMAN::make_numeric_complex_array(std::complex<float> * data,
                                                        vector<int> dims)
{
	size_t total = 1;
	vector<int>::iterator iter = dims.begin();
	while(iter != dims.end()){
		total *= *iter;
		++iter;
	}    

	python::object obj(python::handle<>(PyArray_FromDimsAndData(dims.size(),&dims[0],
																PyArray_CFLOAT, (char*)data)));


	return python::extract<python::numeric::array>(obj);
}

python::numeric::array EMNumPy::em2numpy(EMData *image)
{
	float * data = image->get_data();
	int nx = image->get_xsize();
    int ny = image->get_ysize();
    int nz = image->get_zsize();
	
	vector<int> dims;
	
	dims.push_back(nx);
	
	if (ny > 1) {
		dims.push_back(ny);
	}
	
	if (nz > 1) {
		dims.push_back(nz);
	}
	
	return make_numeric_array(data, dims);
}

void EMNumPy::numpy2em(python::numeric::array& array, EMData* image)
{
	if (!PyArray_Check(array.ptr())) {
		PyErr_SetString(PyExc_ValueError, "expected a PyArrayObject");
		return;
	}
	
	PyArrayObject * array_ptr = (PyArrayObject*) array.ptr();
	int ndim = array_ptr->nd;
	
#if defined (__LP64__) //is it a 64-bit platform?
 	long * dims_ptr = (long*)array_ptr->dimensions;
 	long nx=1, ny=1, nz=1;
#else	//for 32 bit platform
	int * dims_ptr = (int*)array_ptr->dimensions; 
	int nx=1, ny=1, nz=1;
#endif // defined (__LP64__)

	if (ndim <= 0 || ndim > 3) {
		LOGERR("%dD numpy array to EMData is not supported.", ndim);
		return;
	}

	if (ndim == 1) {
		nx = dims_ptr[0];
	}
	else if (ndim == 2) {
		ny = dims_ptr[0];
		nx = dims_ptr[1];
	}
	else if (ndim == 3) {
		nz = dims_ptr[0];
		ny = dims_ptr[1];
		nx = dims_ptr[2];
	}
	
	image->set_size(nx, ny, nz);

	char* array_data = array_ptr->data;
    float* data = image->get_data();
	
	memcpy(data, array_data, sizeof(float) * nx * ny * nz);
	image->done_data();
}

PyObject* EMObject_to_python::convert(EMObject const& emobj)
{

	EMObject::ObjectType t = emobj.get_type();
	PyObject * result = 0;
			
	if (t == EMObject::INT) {
		result = PyInt_FromLong((int)emobj);
	}
	else if (t == EMObject::FLOAT) {
		result = PyFloat_FromDouble((float) emobj);
	}
	else if (t == EMObject::DOUBLE) {
		result = PyFloat_FromDouble((double) emobj);
	}
	else if (t == EMObject::STRING) {
		result = PyString_FromString((const char*) emobj);
	}
	else if (t == EMObject::EMDATA) {
		EMData * img = (EMData*) emobj;
		result = python::incref(python::object(img).ptr());
	}
	else if (t == EMObject::XYDATA) {
		XYData * xyd = (XYData*) emobj;
		result = python::incref(python::object(xyd).ptr());
	}
	else if (t == EMObject::TRANSFORM3D ) {
		Transform3D * trans = (Transform3D*) emobj;
		result = python::incref(python::object(trans).ptr());
	}
	else if (t == EMObject::FLOATARRAY) {
		vector<float> farray = emobj;
		python::list flist;
	    
		for (size_t i = 0; i < farray.size(); i++) {
			flist.append(farray[i]);
		}

		result = python::incref(python::list(flist).ptr());
	}
	else if (t == EMObject::STRINGARRAY) {
		vector<string> strarray = emobj;
		python::list flist;
	    
		for (size_t i = 0; i < strarray.size(); i++) {
			flist.append(strarray[i]);
		}
		
		result = python::incref(python::list(flist).ptr());
	}
	else if (t == EMObject::UNKNOWN) {
		result = Py_None;
	}

	return result;
}
#if 0

PyObject* MArray2D_to_python::convert(MArray2D const & marray2d)
{
    vector<int> dims;
    const size_t * shape = marray2d.shape();
    int ndim = marray2d.num_dimensions();
    for (int i = 0; i <= ndim-1; i++) {
        dims.push_back(shape[i]);
    }

    float * data = (float*)marray2d.data();
    python::numeric::array numarray = make_numeric_array(data, dims);
    
    return python::incref(numarray.ptr());
}
#endif
