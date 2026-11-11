# Troubleshooting local setup

Use this guide if the application does not start after downloading or cloning the repository. Follow the [README](README.md#run-locally) for the normal setup first.

Commands below use Windows PowerShell. Run backend commands from the project root (the folder containing `requirements.txt`). On macOS/Linux, use `python3` instead of `python`, `.venv/bin/python` instead of `.\.venv\Scripts\python.exe`, and `npm` instead of `npm.cmd`.

## Python, Node.js, or npm is not recognised

Install the prerequisites listed in the README, then close and reopen your terminal. Check that these commands print version numbers:

```powershell
python --version
node --version
npm.cmd --version
```

The backend was verified locally with Python 3.11. If you have several Python versions installed, check which one you use when creating `.venv`.

## Backend: NumPy or Pydantic import errors

**Symptoms:** Errors such as `No module named 'numpy._core._multiarray_umath'`, `Importing the numpy C-extensions failed`, or `cannot import name 'ArgsKwargs'` from Pydantic Core.

**Likely cause:** The installed packages do not match the Python interpreter. Some dependencies contain compiled code for a particular Python version. For example, NumPy files marked `cp311` are built for Python 3.11 and cannot be loaded by Python 3.15. This mismatch occurred during local setup.

**Fix:** Stop the backend with `Ctrl+C`. With Python 3.11 installed, use the Windows Python launcher to reconfigure the environment and reinstall its packages:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --force-reinstall -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m uvicorn backend.api:app --reload
```

If `py` is unavailable, use the full path to your Python 3.11 executable for the first command. On macOS/Linux, use `python3.11 -m venv .venv` if installed. `--force-reinstall` replaces existing packages even when pip considers their versions already installed; a normal install left an incompatible Pydantic dependency in place during local setup.

Create the environment on your own computer. Avoid copying `.venv` from another computer or reusing it after switching Python versions without reinstalling its dependencies.

## Backend: missing packages or project files

For `No module named uvicorn`, `fastapi`, or `pandas`, install the dependencies using the project's Python:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If `.venv\Scripts\python.exe` does not exist, create the environment using the README instructions first. Using its full relative path ensures installation and startup use the same Python; activation is optional.

For `No module named backend`, run the startup command from the project root. For a missing CSV file error, check that you downloaded the complete repository, including the `data` folder, and kept its folder structure.

## Frontend: PowerShell blocks npm, or Vite is missing

If PowerShell says `npm.ps1 cannot be loaded because running scripts is disabled`, use `npm.cmd`. If startup reports that Vite is missing, install the frontend dependencies first:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Run these commands from the project root, or omit `cd frontend` if already in that folder. You do not need to change PowerShell's execution policy.

## Package installation fails to connect

Connection timeouts, proxy errors, or `WinError 10013` can mean the terminal cannot reach the package registry. Check your internet connection and whether your network or development environment restricts access to PyPI (Python) or the npm registry (JavaScript). On a managed network, ask your administrator about the required proxy settings.

After resolving the connection problem, repeat `pip install -r requirements.txt` with the project's Python, or `npm.cmd ci` inside `frontend`. If pip reports `No matching distribution found`, read the preceding messages: connection failures and incompatible Python versions need different fixes. For a Python compatibility problem, try the Python 3.11 setup above.

## A port is already in use

The backend uses port **8000**; the frontend normally uses **5173**. If an earlier copy is running in another terminal, stop it there with `Ctrl+C`, then start the server again. Avoid stopping an unfamiliar process.

Vite may choose another port when 5173 is occupied; open the address it prints. If you change the backend port, also update the `/api` proxy target in `frontend/vite.config.js` and restart Vite.

## The dashboard cannot load data

Keep both the backend and frontend terminals running. Open the address printed by Vite, normally **http://127.0.0.1:5173/**.

1. Open **http://127.0.0.1:8000/api/report**. It should return JSON containing promotion data. If it fails, check the backend terminal for an error and use the relevant fix above.
2. Open **http://127.0.0.1:5173/api/report** (adjust the port if Vite chose another). It should return the same report. If only this request fails, check the proxy target in `frontend/vite.config.js` and restart Vite.
3. Refresh the dashboard after fixing the connection. The frontend loads its data when the page opens.

Use `npm.cmd run dev` for local setup. Opening `frontend/index.html` directly does not start Vite or its API proxy. A successful `npm.cmd run build` creates frontend files; it does not start either server.

## Check the setup after a fix

From the project root:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Inside `frontend`:

```powershell
npm.cmd run build
```

During local verification on Windows with Python 3.11, all 8 Python tests and the frontend build passed. Both API routes (`/api/report` and `/api/results.csv`) worked directly and through Vite; the CSV matched the included `results.csv`. A fresh installation on another computer, macOS/Linux commands, and browser interactions were not verified.

If an issue remains, include the full terminal error, the command you ran, your operating system, and your Python/Node.js versions when reporting it.
