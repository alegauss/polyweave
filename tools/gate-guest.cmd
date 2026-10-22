@echo off
rem The gate as the VMware guest runs it, from the root of the tree tools\gate-vm.cmd carried in.
rem
rem The guest is provisioned once by hand with what the host has: Python 3.13 with bpy, pedalboard,
rem demucs, the dev extras and hatchling with editables (the install below builds offline), node,
rem ffmpeg, Godot 4.7.1, FluidSynth, the SoundFont and Surge XT, the tools under C:\Dev. Their
rem places are set here rather than in the guest's own environment, because a program vmrun starts
rem inherits the session it was started in, not what was set after it.
setlocal

set "PY=%LOCALAPPDATA%\Programs\Python\Python313"
set "GODOT=C:\Dev\godot\Godot_v4.7.1-stable_win64_console.exe"
set "SOUNDFONT=C:\Dev\soundfonts\GeneralUser-GS.sf2"

rem The guest has no Vulkan, so Godot falls back to the OpenGL 4.3 of VMware's SVGA driver, and
rem two Godot windows drawing on it at once crash the guest's kernel (0x3B, 0xC2, 2026-10-22; four
rem workers did it in under a minute, and the same tests one at a time never did). So the rest runs
rem on every core without Godot, and the tests that skipped for it run again alone. Mesa's own
rem opengl32.dll beside Godot was tried and could not make a window at all.
set "POLYWEAVE_GATE_GODOT_ALONE=1"
set "PATH=%PY%;%PY%\Scripts;C:\Dev\node;C:\Dev\ffmpeg\bin;C:\Dev\fluidsynth\fluidsynth-v2.6.1-win10-x64-cpp11\bin;%PATH%"

rem The carry brings the files and not .git, and the gate's own test asks git what it ignores.
if not exist .git git init -q

rem The tree is extracted fresh each run, so it is installed again; the dependencies already are.
python -m pip install --quiet --no-deps --no-build-isolation -e . || exit /b 1

rem The window's half of the gate needs its node_modules, which the carry leaves out.
pushd gui
call npm ci --no-audit --no-fund --loglevel=error
if errorlevel 1 (popd & exit /b 1)
popd

python tools\gate.py
exit /b %ERRORLEVEL%
