import logging
import sys
from time import sleep

import numpy as np
from meer_tec.interfaces import USB
from meer_tec.tec import TEC
from mog_qrf import QRF
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import Procedure, Results
from pymeasure.experiment.parameters import FloatParameter, IntegerParameter
from pymeasure.experiment.results import unique_filename
from pymeasure.instruments.thorlabs import ThorlabsPM100USB

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class FilterCellProcedure(Procedure):
    start_frequency = FloatParameter(
        "Start frequency of the ramp",
        units="MHz",
        default=10.0,
        minimum=1.0,
        maximum=250.0,
    )

    stop_frequency = FloatParameter(
        "Start frequency of the ramp",
        units="MHz",
        default=50.0,
        minimum=1.0,
        maximum=250.0,
    )

    frequency_step = FloatParameter(
        "Size of the frequency step",
        units="MHz",
        default=1.0,
        minimum=0.00001,
        maximum=10.0,
    )

    channel = IntegerParameter(
        "Channel for the frequency sweep", default=1, minimum=1, maximum=4
    )

    step_time = FloatParameter(
        "Wait time between frequency steps",
        units="s",
        default=1.0,
        minimum=0.1,
        maximum=10.0,
    )

    cell_temperature = FloatParameter(
        "Temperature of the filter cell",
        units="C",
        default=40.0,
        minimum=0.0,
        maximum=100.0,
    )

    max_heat_time = FloatParameter(
        "Maximum time to heat the cell to the desired temperature",
        units="s",
        default=60.0,
        minimum=10.0,
        maximum=600.0,
    )

    DATA_COLUMNS = ["Frequency", "Power"]

    def startup(self):
        log.info("Connecting to MOGlabs QRF")
        self.qrf = QRF("192.168.0.103")
        self.pm = ThorlabsPM100USB()
        usb = USB()
        self.tec = TEC(usb)

    def execute(self):
        log.info("Heating the filter cell to the desired temperature.")
        self.tec.object_temperature = self.cell_temperature
        elapsed_time = 0
        while not self.tec.is_stable:
            elapsed_time += 1
            sleep(1)
            if elapsed_time >= self.max_heat_time:
                log.error("Temperature of the filter cell did not stabilize in time.")
                break

        if self.tec.is_stable:
            log.info("Temperature of the filter cell stabilized.")

        freqs = np.arange(
            self.start_frequency, self.stop_frequency, self.frequency_step
        )

        log.info("Start recording absorption spectrum.")
        for f in freqs:
            self.qrf.freq(self.channel, f)
            p = self.pm.power()
            sleep(self.step_time)
            self.emit("results", {"Frequency": f, "Power": p})

        if self.should_stop():
            log.warning("Caught the stop flag in the procedure")
            return


class MainWindow(ManagedWindow):
    def __init__(self):
        super(MainWindow, self).__init__(
            procedure_class=FilterCellProcedure,
            inputs=[
                "channel",
                "start_frequency",
                "stop_frequency",
                "frequency_step",
                "step_time",
                "cell_temperature",
                "max_heat_time",
            ],
            displays=["start_frequency", "stop_frequency", "frequency_step"],
            x_axis="Frequency",
            y_axis="Power",
            directory_input=True,
            sequencer=True,
            sequencer_inputs=[
                "start_frequency",
                "stop_frequency",
                "frequency_step",
                "cell_temperature",
            ],
        )
        self.setWindowTitle("Absorption spectrum")

    def queue(self, *, procedure=None):
        directory = self.directory
        filename = unique_filename(directory, prefix="AbsorptionSpectrum")

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
