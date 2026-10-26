# Python 3.14.6 and Windows 11 compatibility

The application was installed into a fresh virtual environment using **CPython 3.14.6, Linux x86_64**. `pip check` found no broken requirements. All 52 pinned requirements successfully resolved and downloaded as Windows x86_64 CPython 3.14-compatible or platform-independent wheels. The exact wheel filenames are in `evidence/windows_cp314_wheel_audit.csv`. This is dependency compatibility evidence, not physical Windows execution.

`setup_windows.bat` uses an existing Python 3.14 interpreter, checks an existing virtual environment before reusing it, installs requirements and runs pip check. It does not install another system Python. An existing interpreter can be explicitly selected with `set "ESS_PYTHON=C:\path\to\python.exe"`. `run_windows.bat` launches the local Streamlit server. The included requirements are pinned; wheel installation requires network access on first setup. This ZIP is source distribution, not an offline executable.

Windows 11 batch scripts, native file locking and the complete application were not executed on a physical Windows host. They remain a platform acceptance check. SQLite connections explicitly close before temporary backup deletion, including on Windows. The local application binds to localhost and uses bundled fonts/assets.

Official references consulted:

* https://www.python.org/downloads/release/python-3146/
* https://docs.streamlit.io/get-started/installation/command-line
* https://github.com/scikit-learn/scikit-learn/releases

The executed installation and wheel audit, rather than a general support statement alone, support this release's compatibility assessment.
