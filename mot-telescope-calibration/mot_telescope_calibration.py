import logging
import sys
from pathlib import Path
from time import sleep

import numpy as np
from adboxes import TelescopeADBox
from mogdevice.qrf import QRF
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows.managed_dock_window import ManagedDockWindow
from pymeasure.experiment import Procedure
from pymeasure.experiment.parameters import FloatParameter, ListParameter

SLEEP_TIME = 0.1

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


def get_power_values(start, stop):
    all_power_levels = np.loadtxt(
        Path(__file__).parent / "possible_power_values_qrf.txt"
    )
    rf_powers = all_power_levels[all_power_levels >= start]
    rf_powers = rf_powers[rf_powers <= stop]
    return rf_powers


class ReadoutPowerLevelProcedure(Procedure):

    start_rf_power = FloatParameter(
        "rf power start",
        default=0.0,
        units="dBm",
        minimum=-50.0,
        maximum=34.5,
    )

    stop_rf_power = FloatParameter(
        "rf power stop",
        default=33.0,
        units="dBm",
        minimum=-50.0,
        maximum=34.5,
    )

    qrf_channel = ListParameter(
        "QRF channel",
        default=4,
        choices=[1, 2, 3, 4],
    )

    DATA_COLUMNS = ["rf power", "a1", "a2", "a3", "b1", "b2", "b3"]

    def startup(self):
        log.info("Connecting to Telescope AD Box")
        self.adbox = TelescopeADBox("ASRL10::INSTR")
        log.info("Connecting to QRF")
        self.qrf = QRF("192.168.123.51")

    def get_estimates(self):
        factor = 1.5  # roughly determined...
        n_points = len(get_power_values(self.start_rf_power, self.stop_rf_power))
        estimates = [
            ("Duration / s", f"{factor * n_points * SLEEP_TIME:.1f}"),
        ]
        return estimates

    def execute(self):
        rf_powers = get_power_values(self.start_rf_power, self.stop_rf_power)
        n_points = len(rf_powers)

        for i, rf_power in enumerate(rf_powers):
            self.qrf.channels[self.qrf_channel].power = rf_power
            sleep(SLEEP_TIME)
            adc_values = self.adbox.get_data(raw=True)
            self.emit("progress", 100 * i / n_points)
            self.emit(
                "results",
                {
                    "rf power": rf_power,
                    "a1": adc_values["A1"],
                    "a2": adc_values["A2"],
                    "a3": adc_values["A3"],
                    "b1": adc_values["B1"],
                    "b2": adc_values["B2"],
                    "b3": adc_values["B3"],
                },
            )


class MainWindow(ManagedDockWindow):
    def __init__(self):
        super(MainWindow, self).__init__(
            procedure_class=ReadoutPowerLevelProcedure,
            inputs=[
                "start_rf_power",
                "stop_rf_power",
                "qrf_channel",
            ],
            displays=[
                "start_rf_power",
                "stop_rf_power",
                "qrf_channel",
            ],
            x_axis=["rf power", "rf power"],
            y_axis=["a1", "b1"],
            enable_file_input=True,
        )
        self.setWindowTitle("QRF power vs. ADBox ADC values")
        self.filename = "adc_values.csv"


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
