SET builddir=%SRC_DIR%\..\build_eman
if errorlevel 1 exit 1

mkdir %builddir% && cd %builddir%
if errorlevel 1 exit 1

set CL=/MP

cmake "%SRC_DIR%" -G "Visual Studio 9 2008 Win64" ^
                    -DCMAKE_BUILD_TYPE=Release
if errorlevel 1 exit 1

cmake --build "%builddir%" --config Release --target install
if errorlevel 1 exit 1

set "PATH=c:\\EMAN2\bin;%PATH%"
set "PYTHONPATH=c:\\EMAN2\lib;%SP_DIR%;%PYTHONPATH%"
e2version.py
if errorlevel 1 exit 1
e2speedtest.py
if errorlevel 1 exit 1
e2display.py -h
if errorlevel 1 exit 1
