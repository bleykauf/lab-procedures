import logging
import sys
from time import sleep

import numpy as np
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import Procedure, Results
from pymeasure.experiment.parameters import FloatParameter, ListParameter
from pymeasure.experiment.results import unique_filename
from pymeasure.instruments.rohdeschwarz.hmp import HMP4040
from pymeasure.instruments.thorlabs import ThorlabsPM100USB

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class AOMAmplifierProcedure(Procedure):
    start_voltage = FloatParameter(
        "Start voltage of the ramp",
        units="V",
        default=0.0,
        minimum=0.0,
        maximum=10.0,
    )

    stop_voltage = FloatParameter(
        "Stop voltage of the ramp",
        units="V",
        default=10.0,
        minimum=0.0,
        maximum=10.0,
    )

    voltage_step = FloatParameter(
        "Size of the voltage step",
        units="V",
        default=0.1,
        minimum=0.00001,
        maximum=10.0,
    )

    hmp_channel = ListParameter("HMP4040 channel", default=1, choices=[1, 2, 3, 4])

    step_time = FloatParameter(
        "Wait time between voltage steps",
        units="s",
        default=0.1,
        minimum=0.001,
        maximum=10.0,
    )

    DATA_COLUMNS = ["Voltage", "Power"]

    def get_voltages(self):
        voltages = np.arange(
            self.start_voltage,
            self.stop_voltage + self.voltage_step,
            self.voltage_step,
        )
        return voltages

    def startup(self):
        self.pm = ThorlabsPM100USB("USB0::0x1313::0x8078::P0029762::INSTR")
        self.hmp = HMP4040("ASRL11::INSTR")
        self.hmp.selected_channel = self.hmp_channel

    def get_estimates(self):
        n_points = len(self.get_voltages())
        estimates = [
            ("Duration / s", f"{n_points * self.step_time:.1f}"),
        ]
        return estimates

    def execute(self):
        voltages = self.get_voltages()

        for i, v in enumerate(voltages):
            self.emit("progress", 100 * (i / len(voltages)))
            self.hmp.voltage = v
            sleep(self.step_time)
            p = self.pm.power
            self.emit("results", {"Voltage": v, "Power": p})

        self.hmp.voltage = self.start_voltage

        if self.should_stop():
            log.warning("Caught the stop flag in the procedure")
            return


class MainWindow(ManagedWindow):
    def __init__(self):
        super(MainWindow, self).__init__(
            procedure_class=AOMAmplifierProcedure,
            inputs=[
                "start_voltage",
                "stop_voltage",
                "voltage_step",
                "step_time",
                "hmp_channel",
            ],
            displays=["start_voltage", "stop_voltage", "voltage_step"],
            x_axis="Voltage",
            y_axis="Power",
            enable_file_input=True,
        )
        self.setWindowTitle("AOM Amplifier Calibration")

    def queue(self, *, procedure=None):
        directory = self.directory
        filename = unique_filename(directory, prefix="AOMAmplifierCalibration")

        if procedure is None:
            procedure = self.make_procedure()
        results = Results(procedure, filename)

        experiment = self.new_experiment(results)

        self.manager.queue(experiment)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
