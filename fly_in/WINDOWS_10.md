# Running Fly-in on Windows 10

This guide uses **PowerShell**. The commands assume you have downloaded or
cloned the repository and opened PowerShell at its root.

## 1. Install Python

Install **64-bit Python 3.10 or later** from
[python.org](https://www.python.org/downloads/windows/). During installation,
check **Add Python to PATH**. The official installer also installs the `py`
launcher.

Check that Python is available:

```powershell
py -3 --version
```

The reported version must be 3.10 or later.

## 2. Open the project folder

In PowerShell, go to the repository root and then enter the project folder:

```powershell
cd .\fly_in
```

If the project files are already in the current folder (including `fly_in.py`,
`requirements.txt`, and `maps`), stay there. Verify that you are in the right
location:

```powershell
Get-ChildItem fly_in.py, requirements.txt, maps
```

## 3. Create a virtual environment and install dependencies

Create a virtual environment to isolate the project's dependencies, activate
it, and install the required packages:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks script activation, allow scripts for the current
PowerShell session only, then try again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Alternatively, you can skip activation and call Python from the virtual
environment directly:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If you use this alternative, replace `python` with
`.\.venv\Scripts\python.exe` in the commands below.

## 4. Run the project

With the virtual environment activated, launch the 2D graphical application:

```powershell
python .\fly_in.py
```

Other available modes:

```powershell
# Solve a map in the terminal
python .\fly_in.py .\maps\02_simple_fork.txt

# Solve a map, then open the 2D viewer
python .\fly_in.py .\maps\02_simple_fork.txt --gui

# Open the isometric 3D viewer
python .\fly_in.py --3d

# Solve a map, then display it in the 3D viewer
python .\fly_in.py .\maps\02_simple_fork.txt --3d
```

## 5. Run the tests

The tests cover the engine, maps, and viewers:

```powershell
python -m unittest discover -s tests -t .
```

## Troubleshooting

- **`py` is not recognized**: reinstall Python from python.org and enable
  adding it to `PATH`, or open a new terminal after installation.
- **`No module named ...`**: make sure the `.venv` environment is activated,
  then run `python -m pip install -r requirements.txt` again.
- **The script cannot find maps or assets**: make sure PowerShell is in the
  folder containing `fly_in.py`, `maps/`, and `assets/`.
- **The graphical window does not open**: make sure your Windows graphics
  drivers are up to date. To test the engine separately, run a map without
  `--gui` or `--3d`.

When you are finished, exit the virtual environment with:

```powershell
deactivate
```
