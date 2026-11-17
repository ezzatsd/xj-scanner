"""Prototype OBD-II read-only scanner for a 2016 Volkswagen Polo.

The current version works only with the built-in simulator. Run the graphical
interface with:

    python3 pc/obd_scan.py

Or use the text interface with:

    python3 pc/obd_scan.py --cli DEMO --seconds 5

It prints engine speed and coolant temperature, then records the same values
in a timestamped CSV file under ``pc/logs``.
"""

import argparse
import csv
import datetime
import os
import time

from obd_protocol import DemoSource, LinkError, PARAMS, PARAMS_BY_PID


LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")


class CsvLog:
    """Write timestamped parameter samples to one CSV file."""

    def __init__(self, params):
        os.makedirs(LOG_DIR, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = os.path.join(LOG_DIR, f"obd_{stamp}.csv")
        self.params = list(params)
        self.file = open(self.path, "w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)
        self.writer.writerow(
            ["time", "elapsed_s"] + [param.label for param in self.params]
        )
        self.started_at = time.monotonic()

    def write(self, values):
        now = datetime.datetime.now().isoformat(timespec="milliseconds")
        elapsed = time.monotonic() - self.started_at
        row = [now, f"{elapsed:.2f}"]
        row.extend(values.get(param.pid, "") for param in self.params)
        self.writer.writerow(row)
        self.file.flush()

    def close(self):
        self.file.close()


def open_source(name):
    """Open a named data source without ever contacting a vehicle."""

    if name.upper() == "DEMO":
        return DemoSource()
    raise LinkError(
        f"Source inconnue : {name}. Seule la source simulée DEMO est disponible."
    )


def run_cli(source_name, seconds, interval):
    """Display and log simulated values for a limited duration."""

    source = open_source(source_name)
    log = CsvLog(PARAMS)
    print("Source : DEMO (aucun véhicule connecté)")
    print(f"Enregistrement : {log.path}")

    stop_at = time.monotonic() + seconds
    try:
        while time.monotonic() < stop_at:
            values = {
                param.pid: source.read_param(param.pid)
                for param in PARAMS
            }
            log.write(values)
            fields = [
                f"{PARAMS_BY_PID[pid].name} : {value} "
                f"{PARAMS_BY_PID[pid].unit}"
                for pid, value in values.items()
            ]
            print(" | ".join(fields), flush=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Arrêt demandé.")
    finally:
        log.close()
        source.close()
        print(f"CSV enregistré : {log.path}")


def run_gui():
    """Display the two simulated values in a small Tkinter window."""

    import tkinter as tk
    from tkinter import ttk

    root = tk.Tk()
    root.title("Polo OBD-II — Démonstration")
    root.geometry("680x390")
    root.minsize(600, 360)

    main_frame = ttk.Frame(root, padding=20)
    main_frame.pack(fill="both", expand=True)

    ttk.Label(
        main_frame,
        text="Diagnostic OBD-II en lecture seule",
        font=("TkDefaultFont", 18, "bold"),
    ).pack(anchor="w")
    ttk.Label(
        main_frame,
        text="Mode DEMO — aucun véhicule connecté",
    ).pack(anchor="w", pady=(2, 18))

    values_frame = ttk.Frame(main_frame)
    values_frame.pack(fill="x")
    value_vars = {}
    for param in PARAMS:
        row = ttk.Frame(values_frame, padding=(0, 7))
        row.pack(fill="x")
        ttk.Label(row, text=param.name, width=38).pack(side="left")
        value_var = tk.StringVar(value="—")
        value_vars[param.pid] = value_var
        ttk.Label(
            row,
            textvariable=value_var,
            font=("TkDefaultFont", 17, "bold"),
            width=10,
            anchor="e",
        ).pack(side="left")
        ttk.Label(row, text=param.unit, width=8).pack(side="left", padx=(8, 0))

    status_var = tk.StringVar(value="Simulation arrêtée")
    ttk.Separator(main_frame).pack(fill="x", pady=(15, 10))
    ttk.Label(main_frame, textvariable=status_var).pack(anchor="w")

    buttons = ttk.Frame(main_frame)
    buttons.pack(fill="x", pady=(12, 0))
    start_button = ttk.Button(buttons, text="Démarrer")
    start_button.pack(side="left")
    stop_button = ttk.Button(buttons, text="Arrêter", state="disabled")
    stop_button.pack(side="left", padx=(8, 0))
    log_button = ttk.Button(
        buttons,
        text="Démarrer l’enregistrement",
        state="disabled",
    )
    log_button.pack(side="left", padx=(18, 0))

    log_status_var = tk.StringVar(value="Aucun enregistrement CSV en cours")
    ttk.Label(
        main_frame,
        textvariable=log_status_var,
        wraplength=630,
    ).pack(anchor="w", pady=(12, 0))

    state = {"running": False, "source": None, "log": None}

    def stop_logging():
        if state["log"] is None:
            return
        path = state["log"].path
        state["log"].close()
        state["log"] = None
        log_button["text"] = "Démarrer l’enregistrement"
        log_status_var.set(f"CSV enregistré : {path}")

    def toggle_logging():
        if state["log"] is not None:
            stop_logging()
            return
        if not state["running"]:
            return
        state["log"] = CsvLog(PARAMS)
        log_button["text"] = "Arrêter l’enregistrement"
        log_status_var.set(f"Enregistrement en cours : {state['log'].path}")

    def stop_demo():
        stop_logging()
        state["running"] = False
        if state["source"] is not None:
            state["source"].close()
            state["source"] = None
        start_button["state"] = "normal"
        stop_button["state"] = "disabled"
        log_button["state"] = "disabled"
        status_var.set("Simulation arrêtée")

    def start_demo():
        if state["source"] is not None:
            state["source"].close()
        state["source"] = DemoSource()
        state["running"] = True
        start_button["state"] = "disabled"
        stop_button["state"] = "normal"
        log_button["state"] = "normal"
        status_var.set("Simulation en cours — mise à jour toutes les 0,5 s")

    def refresh_values():
        if state["running"] and state["source"] is not None:
            try:
                values = {}
                for param in PARAMS:
                    values[param.pid] = state["source"].read_param(param.pid)
                    value_vars[param.pid].set(values[param.pid])
                if state["log"] is not None:
                    state["log"].write(values)
            except LinkError as error:
                stop_demo()
                status_var.set(f"Erreur : {error}")
        root.after(500, refresh_values)

    def close_window():
        stop_demo()
        root.destroy()

    start_button["command"] = start_demo
    stop_button["command"] = stop_demo
    log_button["command"] = toggle_logging
    root.protocol("WM_DELETE_WINDOW", close_window)
    refresh_values()
    root.mainloop()


def positive_float(text):
    value = float(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("la valeur doit être supérieure à zéro")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cli",
        metavar="SOURCE",
        help="mode texte avec cette source ; seule DEMO est disponible",
    )
    parser.add_argument(
        "--seconds",
        type=positive_float,
        default=10.0,
        help="durée du relevé simulé en secondes (défaut : 10)",
    )
    parser.add_argument(
        "--interval",
        type=positive_float,
        default=0.5,
        help="intervalle entre deux mesures en secondes (défaut : 0,5)",
    )
    args = parser.parse_args()

    if args.cli:
        try:
            run_cli(args.cli, args.seconds, args.interval)
        except LinkError as error:
            parser.error(str(error))
    else:
        run_gui()


if __name__ == "__main__":
    main()
