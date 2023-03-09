:: --------------------------------------------
:: This file is for easier automation purposes.
:: --------------------------------------------
@echo off
echo %date% %time% >> %~dp0\log.txt
cd %~dp0
%~dp0\.venv\Scripts\pythonw.exe %~dp0\generator.py %* >> %~dp0\log.txt 2>&1
echo ---------------------- >> %~dp0\log.txt
exit