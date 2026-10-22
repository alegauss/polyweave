@echo off
rem The gate in the VMware guest, so the desk somebody is working at stays theirs.
rem
rem A full gate opens Godot windows and runs Blender and the engine for a quarter of an hour, and the
rem person at the host cannot use it meanwhile. This hands the run to winwright's guest runner, which
rem carries the working tree into the test VM, runs tools\gate-guest.cmd there and brings the logs
rem back to TestResults\vm. The VM and its credentials are winwright's: see the notes at the top of
rem winwright\tools\run-tests-vm.ps1, which also says the guest is never provisioned by a script.
rem
rem   tools\gate-vm.cmd            the whole gate in the guest
rem   tools\gate-vm.cmd -Bound 90  any of the runner's own flags pass through
setlocal

set "RUNNER=%WINWRIGHT_HOME%"
if "%RUNNER%"=="" set "RUNNER=%~dp0..\..\winwright"
set "RUNNER=%RUNNER%\tools\run-tests-vm.ps1"
if not exist "%RUNNER%" (
  echo gate-vm: winwright's runner is not at %RUNNER%; set WINWRIGHT_HOME to its checkout
  exit /b 3
)

rem -Command and not -File, so -Bring arrives as a list rather than one string with commas in it.
powershell -NoProfile -ExecutionPolicy Bypass -Command "& '%RUNNER%' -Tree '%~dp0..' -Name polyweave -Run 'tools\gate-guest.cmd' -ResultsIn '.polyweave\gate' -Bring 'pytest.log','stamp.json','gui.log' %*; exit $LASTEXITCODE"
exit /b %ERRORLEVEL%
