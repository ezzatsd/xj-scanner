"""Prototype OBD-II read-only scanner for a 2016 Volkswagen Polo.

The current version works only with the built-in simulator:

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
        required=True,
        help="source de données ; seule DEMO est disponible pour le moment",
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

    try:
        run_cli(args.cli, args.seconds, args.interval)
    except LinkError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
