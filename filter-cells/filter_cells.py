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
from pymeasure.experiment.parameters import FloatParameter, ListParameter
from pymeasure.experiment.results import unique_filename
from pymeasure.instruments.thorlabs import ThorlabsPM100USB

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class FilterCellProcedure(Procedure):
    start_frequency = FloatParameter(
        "Start frequency of the ramp",
        units="MHz",
        default=110.0,
        minimum=4.0,
        maximum=250.0,
    )

    stop_frequency = FloatParameter(
        "Stop frequency of the ramp",
        units="MHz",
        default=250.0,
        minimum=1.0,
        maximum=250.0,
    )

    frequency_step = FloatParameter(
        "Size of the frequency step",
        units="MHz",
        default=0.1,
        minimum=0.00001,
        maximum=10.0,
    )

    qrf_channel = ListParameter("QRF channel", default=2, choices=[1, 2, 3, 4])

    step_time = FloatParameter(
        "Wait time between frequency steps",
        units="s",
        default=0.01,
        minimum=0.001,
        maximum=10.0,
    )

    cell_temperature = FloatParameter(
        "Temperature of the filter cell",
        units="C",
        default=60.0,
        minimum=0.0,
        maximum=100.0,
    )

    max_heat_time = FloatParameter(
        "Maximum time to wait after setting desired cell temperature",
        units="s",
        default=60.0,
        minimum=10.0,
        maximum=600.0,
    )

    thermalization_time = FloatParameter(
        "Waiting period after setting the temperature of the filter cell to the desired value",
        units="s",
        default=180.0,
        minimum=0.0,
        maximum=600.0,
    )

    DATA_COLUMNS = ["Frequency", "Power"]

    def startup(self):
        log.info("Connecting to MOGlabs QRF")
        self.qrf = QRF("192.168.123.51")
        self.pm = ThorlabsPM100USB("USB0::0x1313::0x8078::P0032734::INSTR")
        self.usb = USB("COM3")
        self.tec = TEC(self.usb, 0)

    def execute(self):
        if self.stop_frequency < self.start_frequency:
            self.frequency_step = -self.frequency_step
        freqs = np.arange(
            self.start_frequency,
            self.stop_frequency + self.frequency_step,
            self.frequency_step,
        )

        total_duration = (
            self.max_heat_time + self.thermalization_time + self.step_time * len(freqs)
        )

        self.qrf.set_timeout(2 * total_duration)
        self.qrf.freq(self.qrf_channel, self.start_frequency)
        sleep(
            1
        )  # to avoid a sudden frequency change at the beginning of the measurement

        temp_changed = False
        if self.cell_temperature != self.tec.target_object_temperature:
            temp_changed = True
            log.info(
                f"Heating the filter cell to the desired temperature of {self.cell_temperature} C."
            )

            try:
                self.tec.target_object_temperature = self.cell_temperature
            except ValueError:
                # there is a bug in the library, see https://github.com/bleykauf/meer_tec/issues/4
                pass
        elapsed_time = 0
        while not self.tec.is_stable == 2:
            elapsed_time += 1
            sleep(1)
            if elapsed_time >= self.max_heat_time:
                log.error("Temperature of the filter cell did not stabilize in time.")
                break
        if temp_changed:
            log.info("Waiting for the filter cell to thermalize.")
            sleep(self.thermalization_time)

        if self.tec.is_stable == 2:
            log.info("Temperature of the filter cell stabilized.")

        log.info("Start recording absorption spectrum.")

        for f in freqs:
            self.qrf.freq(self.qrf_channel, f)
            p = self.pm.power
            sleep(self.step_time)
            self.emit("results", {"Frequency": f, "Power": p})
        self.qrf.freq(self.qrf_channel, self.start_frequency)
        self.usb.close()

        if self.should_stop():
            log.warning("Caught the stop flag in the procedure")
            self.usb.close()
            return


class MainWindow(ManagedWindow):
    def __init__(self):
        super(MainWindow, self).__init__(
            procedure_class=FilterCellProcedure,
            inputs=[
                "qrf_channel",
                "start_frequency",
                "stop_frequency",
                "frequency_step",
                "step_time",
                "cell_temperature",
                "max_heat_time",
                "thermalization_time",
            ],
            displays=["cell_temperature", "start_frequency", "stop_frequency"],
            x_axis="Frequency",
            y_axis="Power",
            directory_input=True,
            sequencer=True,
            sequencer_inputs=[
                "cell_temperature",
                "start_frequency",
                "stop_frequency",
                "frequency_step",
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
