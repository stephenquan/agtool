setlocal
set "PYTHON_DIR=C:\Program Files (x86)\Microsoft Visual Studio\Shared\Python36_64"
set PATH="%PYTHON_DIR%";"%PYTHON_DIR%"\Scripts;%PATH

python agtool.py %*
