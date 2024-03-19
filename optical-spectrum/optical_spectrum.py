import logging
import sys
from time import sleep

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import Procedure
from pymeasure.experiment.parameters import (
    BooleanParameter,
    FloatParameter,
    IntegerParameter,
    ListParameter,
)
from pymeasure.instruments.yokogawa.aq6370series import AQ6370D

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class ReadoutPowerLevelProcedure(Procedure):

    resolution_bandwidth = ListParameter(
        "Bandwidth Resolution",
        default=0.1e-9,
        units="m",
        choices=[0.02e-9, 0.05e-9, 0.1e-9, 0.2e-9, 0.5e-9, 1e-9, 2e-9],
    )

    wavelength_start = FloatParameter(
        "Wavelength Start",
        default=7.65e-7,
        units="m",
        minimum=50e-9,
        maximum=1700e-9,
    )

    wavelength_stop = FloatParameter(
        "Wavelength Stop",
        default=8.05e-7,
        units="m",
        minimum=600e-9,
        maximum=2250e-9,
    )

    reference_level = FloatParameter(
        "Reference Level",
        default=0.0,
        units="dBm",
        minimum=-90.0,
        maximum=20.0,
    )

    level_position = IntegerParameter(
        "Level Position",
        default=8,
        minimum=1,
        maximum=12,
    )

    sample_number = IntegerParameter(
        "Number of sampling points",
        default=1001,
        minimum=101,
        maximum=50001,
        group_by="manual_sample_number",
    )

    manual_sample_number = BooleanParameter(
        "Manual sample number",
        default=False,
    )

    DATA_COLUMNS = ["Wavelength", "Power Level"]

    def startup(self):
        log.info("Connecting to AQ6370D")
        self.osa = AQ6370D("TCPIP::192.168.123.169::INSTR")
        self.osa.sweep_mode = "REPEAT"

    def execute(self):
        self.osa.wavelength_start = self.wavelength_start
        self.osa.wavelength_stop = self.wavelength_stop
        self.osa.resolution_bandwidth = self.resolution_bandwidth
        self.osa.reference_level = self.reference_level
        self.osa.level_position = self.level_position
        self.osa.automatic_sample_number = not self.manual_sample_number
        if self.manual_sample_number:
            self.osa.sample_number = self.sample_number
        self.osa.sweep_mode = "SINGLE"
        self.osa.initiate_sweep()
        while self.osa.values(":STAT:OPER:EVEN?")[0]:
            sleep(0.1)
        x_data = self.osa.get_xdata()
        y_data = self.osa.get_ydata()
        for x, y in zip(x_data, y_data):
            self.emit(
                "results",
                {"Wavelength": x, "Power Level": y},
            )

        del self.osa


class MainWindow(ManagedWindow):
    def __init__(self):
        super(MainWindow, self).__init__(
            procedure_class=ReadoutPowerLevelProcedure,
            inputs=[
                "wavelength_start",
                "wavelength_stop",
                "resolution_bandwidth",
                "reference_level",
                "level_position",
                "manual_sample_number",
                "sample_number",
            ],
            displays=[
                "wavelength_start",
                "wavelength_stop",
                "resolution_bandwidth",
                "reference_level",
                "level_position",
                "manual_sample_number",
                "sample_number",
            ],
            x_axis="Wavelength",
            y_axis="Power Level",
            enable_file_input=True,
        )
        self.setWindowTitle("Optical Spectral Analyzer AQ6370D")
        self.filename = "optical_spectrum.csv"


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
