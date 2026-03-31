H125 INTERACTIVE CHECKLIST — Romandy AI Studio
================================================
heliromandie.ch / romandy.tech


WHAT IS THIS
------------
An interactive checklist for the H125 helicopter in Microsoft Flight Simulator.
Items marked AUTO check themselves in real time based on your actual sim state.
Items marked MANUAL are clicked by you when you have physically verified them.


FIRST-TIME SETUP (do this once)
--------------------------------
1. Make sure Python 3.10 or later is installed on your PC.
   Download at https://www.python.org if needed.

2. Open a command prompt (Win+R, type cmd, press Enter).

3. Install the required libraries by typing:

      pip install flask flask-cors SimConnect

   Wait for it to finish. You only need to do this once.


HOW TO USE IT — STEP BY STEP
-----------------------------
Step 1 — Launch MSFS (2020 or 2024).
         Load a flight with the H125. Wait until you are in the cockpit.

Step 2 — Open a command prompt in the folder where you put the files.
         Right-click the folder while holding Shift, choose
         "Open PowerShell window here" or "Open command window here".

Step 3 — Type:

            python server.py

         You should see something like:

            [SimConnect] ✓ Connected — version: 2020
            H125 Checklist Server running on http://localhost:5001

         Leave this window open. Do not close it.

Step 4 — Open h125_checklist.html in your browser.
         (Double-click the file, or drag it into Chrome / Edge / Firefox.)

Step 5 — Check the status badge in the top-right corner.
         GREEN  "MSFS 2020 CONNECTED"  →  everything is working.
         ORANGE "MOCK MODE"            →  MSFS not detected, manual-only mode.
         RED    "SIM OFFLINE"          →  server is not running, go back to Step 3.

Step 6 — Work through the checklist phases using the tab bar at the top:
         Before Starting → Engine Start → Before Takeoff → Hover Check → Shutdown

         AUTO items (blue badge):
           These check themselves when the condition is met in the sim.
           Example: switch the battery ON in MSFS → the Battery item checks itself.
           The live sim value is shown on the right side of each item.

         MANUAL items (amber badge):
           Click the item to check it after you have verified it yourself.
           Click again to uncheck if needed.

Step 7 — When all items in a phase are checked, a "PHASE COMPLETE" message appears.
         Click the next tab to continue to the following phase.

Step 8 — To reset between flights:
         "Reset Manual" clears only the manual items.
         "Reset All"    clears everything and returns to phase 1.


SHUTTING DOWN
-------------
When you are done flying, close the browser tab and press Ctrl+C
in the command prompt to stop the server.


TROUBLESHOOTING
---------------
"server.py is not recognised as a command"
  → Python is not installed or not added to PATH.
    Reinstall Python and tick "Add Python to PATH" during setup.

The badge stays red after launching server.py
  → Make sure MSFS is fully loaded into the cockpit before running server.py.
  → Close server.py (Ctrl+C) and run it again once the sim is ready.

pip install fails
  → Try: pip install flask flask-cors SimConnect --break-system-packages

Port already in use error
  → Another program is using port 5001. Open server.py in Notepad,
    find "port=5001" at the bottom and change it to another number (e.g. 5002).
    Then open h125_checklist.html in Notepad, find "localhost:5001" and
    change it to match.


FILES IN THIS PACKAGE
---------------------
  server.py            — Python backend, reads SimConnect and serves the data
  h125_checklist.html  — The checklist interface, open this in your browser
  README.txt           — This file


LICENSE
-------
Freeware — Romandy AI Studio
Not for redistribution without permission.
