@echo off
rem The gate as the VMware guest runs it, from the root of the tree tools\gate-vm.cmd carried in.
rem
rem The guest is provisioned once by hand with what the host has: Python 3.13 with bpy, pedalboard,
rem demucs, the dev extras and hatchling with editables (the install below builds offline), node,
rem ffmpeg, Godot 4.7.1 with Mesa's opengl32.dll and libgallium_wgl.dll beside it, FluidSynth, the
rem SoundFont and Surge XT, the tools under C:\Dev. Their places are set here rather than in the guest's own environment, because
rem a program vmrun starts inherits the session it was started in, not what was set after it.
setlocal

set "PY=%LOCALAPPDATA%\Programs\Python\Python313"
set "GODOT=C:\Dev\godot\Godot_v4.7.1-stable_win64_console.exe"
set "SOUNDFONT=C:\Dev\soundfonts\GeneralUser-GS.sf2"

rem The guest has no Vulkan, so Godot falls back to OpenGL, and eight workers' Godot windows on
rem VMware's SVGA driver crashed the guest's kernel (0x3B, 2026-10-22). Mesa's opengl32.dll beside
rem Godot draws on the CPU instead, and llvmpipe is named so Mesa does not route back to that driver
rem through D3D12.
set "GALLIUM_DRIVER=llvmpipe"
set "PATH=%PY%;%PY%\Scripts;C:\Dev\node;C:\Dev\ffmpeg\bin;C:\Dev\fluidsynth\fluidsynth-v2.6.1-win10-x64-cpp11\bin;%PATH%"

rem The tree is extracted fresh each run, so it is installed again; the dependencies already are.
python -m pip install --quiet --no-deps --no-build-isolation -e . || exit /b 1

rem The window's half of the gate needs its node_modules, which the carry leaves out.
pushd gui
call npm ci --no-audit --no-fund --loglevel=error
if errorlevel 1 (popd & exit /b 1)
popd

python tools\gate.py
exit /b %ERRORLEVEL%
