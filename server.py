#!/usr/bin/env python3
"""
H125 Interactive Checklist Server
Romandy AI Studio — heliromandie.ch / romandy.tech

Compatible MSFS 2020 et MSFS 2024.
Port : 5001  →  http://localhost:5001
"""

import time
import threading
import subprocess
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS

# ── SimConnect ───────────────────────────────────────────────────────────────
try:
    from SimConnect import SimConnect, AircraftRequests
    SIMCONNECT_AVAILABLE = True
except ImportError:
    SIMCONNECT_AVAILABLE = False
    print("[WARN] SimConnect non disponible — démarrage en mode mock")

# ── Flask ─────────────────────────────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# ── État partagé ──────────────────────────────────────────────────────────────
_state: dict       = {}
_connected: bool   = False
_msfs_version: str = "unknown"   # "2020" | "2024" | "unknown"
_lock = threading.Lock()

# ── Chemins DLL connus ────────────────────────────────────────────────────────
#
#  SimConnect.dll est installée par MSFS dans son dossier, et également
#  par le SDK développeur. On liste les emplacements connus pour les deux
#  versions afin de ne pas dépendre uniquement de la détection par registre.
#
DLL_PATHS_2020 = [
    r"C:\Program Files (x86)\Steam\steamapps\common\MicrosoftFlightSimulator\SimConnect.dll",
    r"C:\Program Files\WindowsApps\Microsoft.FlightSimulator_1.0.0.0_x64__8wekyb3d8bbwe\SimConnect.dll",
    r"C:\MSFS 2020 SDK\SimConnect SDK\lib\SimConnect.dll",
    r"C:\MSFS SDK\SimConnect SDK\lib\SimConnect.dll",
]

DLL_PATHS_2024 = [
    r"C:\Program Files (x86)\Steam\steamapps\common\Microsoft Flight Simulator 2024\SimConnect.dll",
    r"C:\Program Files\WindowsApps\Microsoft.Limitless_1.0.0.0_x64__8wekyb3d8bbwe\SimConnect.dll",
    r"C:\MSFS 2024 SDK\SimConnect SDK\lib\SimConnect.dll",
    r"C:\Program Files (x86)\Steam\steamapps\common\MSFS2024\SimConnect.dll",
]

# ── SimVars ───────────────────────────────────────────────────────────────────
#
#  La grande majorité des SimVars sont identiques entre 2020 et 2024.
#  SIMVARS_2024_OVERRIDES ne liste que les variables qui ont effectivement
#  changé de nom dans le SDK 2024 — à compléter au fur et à mesure des
#  mises à jour Asobo.
#
SIMVARS_BASE = {
    "battery":        "ELECTRICAL_MASTER_BATTERY",
    "avionics":       "AVIONICS_MASTER_SWITCH",
    "eng_combustion": "ENG_COMBUSTION:1",
    "eng_n1":         "TURB_ENG_N1:1",
    "eng_n2":         "TURB_ENG_N2:1",
    "eng_torque":     "ENG_TORQUE:1",
    "eng_tot":        "TURB_ENG_ITT:1",
    "oil_pressure":   "ENG_OIL_PRESSURE:1",
    "oil_temp":       "ENG_OIL_TEMPERATURE:1",
    "rotor_rpm_pct":  "ROTOR_RPM_PCT:1",
    "rotor_brake":    "ROTOR_BRAKE_HANDLE_POS",
    "fuel_qty":       "FUEL_TOTAL_QUANTITY",
    "throttle_pos":   "GENERAL_ENG_THROTTLE_LEVER_POSITION:1",
    "collective":     "COLLECTIVE_POSITION",
    "hydraulic":      "HYDRAULIC_PRESSURE:1",
    "beacon":         "LIGHT_BEACON",
    "nav_lights":     "LIGHT_NAV",
    "strobe":         "LIGHT_STROBE",
    "transponder":    "TRANSPONDER_STATE",
    "altitude":       "INDICATED_ALTITUDE",
    "airspeed":       "AIRSPEED_INDICATED",
    "heading":        "HEADING_INDICATOR",
    "on_ground":      "SIM_ON_GROUND",
    "vertical_speed": "VERTICAL_SPEED",
}

# À compléter si Asobo renomme des vars dans de futures updates 2024
SIMVARS_2024_OVERRIDES: dict = {
    # Exemple :
    # "rotor_brake": "ROTOR_BRAKE_ACTIVE",
}


def get_simvars(version: str) -> dict:
    v = dict(SIMVARS_BASE)
    if version == "2024":
        v.update(SIMVARS_2024_OVERRIDES)
    return v


# ── Détection MSFS ────────────────────────────────────────────────────────────

def detect_msfs_hint() -> str:
    """
    Indice de version basé sur les processus Windows.
    Utilisé uniquement pour ordonner les tentatives de connexion —
    PAS comme source de vérité pour la version réellement connectée.
    Retourne "2020", "2024" ou "unknown".
    """
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=5
        )
        procs = result.stdout.lower()
        # Les deux sims peuvent tourner simultanément — on prend le premier trouvé
        # mais ce n'est qu'un hint, pas une certitude
        if "msfs2024.exe" in procs or "limitless.exe" in procs:
            return "2024"
        if "flightsimulator.exe" in procs:
            return "2020"
    except Exception as e:
        print(f"[detect] Erreur lecture processus : {e}")
    return "unknown"


def infer_version_from_dll(dll_path) -> str:
    """
    Déduit la version MSFS depuis le chemin de DLL utilisé.
    C'est la seule source fiable — indépendante de tasklist.
    """
    if dll_path is None:
        return "unknown"
    p = dll_path.lower()
    if "2024" in p or "limitless" in p:
        return "2024"
    if "flightsimulator" in p or "2020" in p:
        return "2020"
    return "unknown"


def find_dll(version: str):
    """Retourne le premier chemin de DLL existant pour la version donnée, ou None."""
    paths = DLL_PATHS_2024 if version == "2024" else DLL_PATHS_2020
    for p in paths:
        if Path(p).exists():
            return p
    return None


# ── Boucle de polling ─────────────────────────────────────────────────────────

def try_connect(dll_path=None):
    """Tente une connexion SimConnect. Lève une exception si échec."""
    if dll_path:
        print(f"[SimConnect] DLL : {dll_path}")
        sm = SimConnect(dll=dll_path)
    else:
        sm = SimConnect()
    ar = AircraftRequests(sm, _time=500)
    return sm, ar


def build_candidates(hint: str) -> list:
    """
    Construit une liste ordonnée de tuples (dll_path, version_inférée).
    L'ordre favorise la version suggérée par le hint, mais chaque tuple
    porte sa propre version — indépendante du hint.
    """
    candidates = []

    # 1. DLL correspondant au hint (priorité)
    dll_hint = find_dll(hint)
    if dll_hint:
        candidates.append((dll_hint, infer_version_from_dll(dll_hint)))

    # 2. DLL de l'autre version (fallback explicite)
    other = "2020" if hint == "2024" else "2024"
    dll_other = find_dll(other)
    if dll_other and dll_other != dll_hint:
        candidates.append((dll_other, infer_version_from_dll(dll_other)))

    # 3. Auto-détection via registre Windows (version = unknown car on ne sait pas)
    candidates.append((None, "unknown"))

    return candidates


def poll_loop():
    global _state, _connected, _msfs_version

    while True:
        # hint = indice de priorité seulement, PAS source de vérité
        hint = detect_msfs_hint()
        print(f"[detect] hint processus : {hint}")

        candidates = build_candidates(hint)

        # Tentatives : on connecte ET on déduit la version depuis la DLL réelle
        sm = ar = None
        connected_version = "unknown"

        for dll_path, dll_version in candidates:
            try:
                label = dll_path or "registre système"
                print(f"[SimConnect] Tentative → {label} (version inférée : {dll_version})")
                sm, ar = try_connect(dll_path)
                connected_version = dll_version   # ← version réelle, pas le hint
                print(f"[SimConnect] ✓ Connecté — version retenue : {connected_version}")
                break
            except Exception as e:
                print(f"[SimConnect] ✗ Échec : {e}")
                sm = ar = None

        if sm is None:
            with _lock:
                _connected    = False
                _msfs_version = "unknown"
                _state        = {}
            print("[SimConnect] Aucune connexion — retry dans 5s")
            time.sleep(5)
            continue

        with _lock:
            _connected    = True
            _msfs_version = connected_version   # ← jamais le hint

        simvars = get_simvars(connected_version)

        try:
            while True:
                snap = {}
                for key, varname in simvars.items():
                    try:
                        val = ar.get(varname)
                        snap[key] = float(val) if val is not None else None
                    except Exception:
                        snap[key] = None
                with _lock:
                    _state = snap
                time.sleep(0.4)

        except Exception as e:
            print(f"[SimConnect] ✗ Connexion perdue : {e} — retry")
            with _lock:
                _connected    = False
                _msfs_version = "unknown"
                _state        = {}
            time.sleep(3)


# ── Mock data ─────────────────────────────────────────────────────────────────

def mock_state() -> dict:
    return {
        "battery": 1.0, "avionics": 1.0, "eng_combustion": 0.0,
        "eng_n1": 0.0, "eng_n2": 0.0, "eng_torque": 0.0,
        "eng_tot": 15.0, "oil_pressure": 0.0, "oil_temp": 20.0,
        "rotor_rpm_pct": 0.0, "rotor_brake": 1.0, "fuel_qty": 52.0,
        "throttle_pos": 0.0, "collective": 0.0, "hydraulic": 0.0,
        "beacon": 1.0, "nav_lights": 1.0, "strobe": 0.0,
        "transponder": 1.0, "altitude": 1800.0, "airspeed": 0.0,
        "heading": 270.0, "on_ground": 1.0, "vertical_speed": 0.0,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/state")
def get_state():
    if SIMCONNECT_AVAILABLE:
        with _lock:
            return jsonify({
                "connected":    _connected,
                "msfs_version": _msfs_version,
                "mock":         False,
                "vars":         dict(_state),
            })
    return jsonify({
        "connected":    False,
        "msfs_version": "unknown",
        "mock":         True,
        "vars":         mock_state(),
    })


@app.route("/health")
def health():
    with _lock:
        return jsonify({
            "status":       "ok",
            "sim":          _connected,
            "msfs_version": _msfs_version,
            "mock":         not SIMCONNECT_AVAILABLE,
        })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if SIMCONNECT_AVAILABLE:
        threading.Thread(target=poll_loop, daemon=True).start()
    else:
        print("[WARN] Mode mock — installer : pip install SimConnect")

    print("=" * 52)
    print("  H125 Checklist Server — Romandy AI Studio")
    print("  http://localhost:5001")
    print("  Compatibilité : MSFS 2020 + MSFS 2024")
    print("=" * 52)
    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)
