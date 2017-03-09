#!groovy

pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                echo 'Building..'
                prefix='/Users/shadow_walker/anaconda'
                sp_dir=prefix +'/lib/python2.7/site-packages'
                sh 'cd build_eman && /usr/local/bin/cmake .. -DNUMPY_INCLUDE_PATH=' + sp_dir+'/numpy/core/include'+
                                                             '-DBOOST_INCLUDE_PATH='+prefix+'/include'+
                                                             '-DBOOST_LIBRARY='+prefix+'/lib/libboost_python.dylib'+
                                                             '-DFFTW3_INCLUDE_PATH='+prefix+'/include'+
                                                             '-DFFTW3_LIBRARY='+prefix+'/lib/libfftw3f.dylib'+
                                                             '-DFFTW3d_INCLUDE_PATH='+prefix+'/include'+
                                                             '-DFFTW3d_LIBRARY='+prefix+'/lib/libfftw3.dylib'+
                                                             '-DFREETYPE_INCLUDE_PATH='+prefix+'/include/freetype2'+
                                                             '-DFREETYPE_LIBRARY='+prefix+'/lib/libfreetype.dylib'+
                                                             '-DFTGL_INCLUDE_PATH='+prefix+'/include'+
                                                             '-DFTGL_LIBRARY='+prefix+'/lib/libftgl.dylib'+
                                                             '-DGSL_CBLAS_INCLUDE_PATH='+prefix+'/include'+
                                                             '-DGSL_CBLAS_LIBRARY='+prefix+'/lib/libgslcblas.dylib'+
                                                             '-DGSL_INCLUDE_PATH='+prefix+'/include'+
                                                             '-DGSL_LIBRARY='+prefix+'/lib/libgsl.dylib'+
                                                             '-DHDF5_INCLUDE_PATH='+prefix+'/include'+
                                                             '-DHDF5_LIBRARY='+prefix+'/lib/libhdf5.dylib'+
                                                             '-DJPEG_INCLUDE_PATH='+prefix+'/include'+
                                                             '-DJPEG_LIBRARY='+prefix+'/lib/libjpeg.dylib'+
                                                             '-DPNG_INCLUDE_PATH='+prefix+'/include'+
                                                             '-DPNG_LIBRARY='+prefix+'/lib/libpng.dylib'+
                                                             '-DPYTHON_INCLUDE_PATH='+prefix+'/include/python2.7'+
                                                             '-DPYTHON_LIBRARY='+prefix+'/lib/libpython2.7.dylib'+
                                                             '-DTIFF_INCLUDE_PATH='+prefix+'/include'+
                                                             '-DTIFF_LIBRARY='+prefix+'/lib/libtiff.dylib'+
                                                             '-DZLIB_LIBRARY='+prefix+'/lib/libz.dylib'
'
            }
        }
        stage('Test') {
            steps {
                echo 'Testing..'
            }
        }
        stage('Deploy') {
            steps {
                echo 'Deploying....'
            }
        }
    }
}
