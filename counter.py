import logging
import sys
from time import sleep

import numpy as np
from pymeasure.display.Qt import QtGui
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import Procedure, Results
from pymeasure.experiment.parameters import (
    FloatParameter,
    IntegerParameter,
    ListParameter,
)
from pymeasure.experiment.results import unique_filename
from pymeasure.instruments import Instrument
from pymeasure.instruments.pendulum import CNT91

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class CounterTimeseriesProcedure(Procedure):

    n_samples = IntegerParameter(
        "Number of samples", default=int(1e3), minimum=1, maximum=int(1e5)
    )
    sample_rate = FloatParameter(
        "Sample rate", units="Hz", default=1e3, maximum=1e5
    )
    channel = ListParameter(
        "Channel", default="B", choices=["A", "B", "C", "E", "INTREF"]
    )
    trigger_source = ListParameter(
        "Trigger Source", default="None", choices=["None", "A", "B", "E"]
    )

    DATA_COLUMNS = ["Time", "Frequency"]

    def startup(self):
        log.info("Connecting to Pendulum CNT9x")
        self.counter = CNT91("USB0::0x14EB::0x0091::956628::INSTR")

    def execute(self):
        log.info("Recording time series.")

        duration = self.n_samples / self.sample_rate

        trigger_source = self.trigger_source
        if trigger_source == "None":
            log.debug("No trigger source selected.")
            trigger_source = None

        log.info("Measurement duration is {}s".format(duration))

        self.counter.buffer_frequency_time_series(
            self.channel, self.n_samples, self.sample_rate, trigger_source=None
        )

        freqs = self.counter.read_buffer(expected_length=self.n_samples)

        time = np.linspace(0, duration, num=len(freqs))

        for t, f in zip(time, freqs):
            self.emit("results", {"Time": t, "Frequency": f})

        if self.should_stop():
            log.warning("Caught the stop flag in the procedure")
            return


class MainWindow(ManagedWindow):
    def __init__(self):
        super(MainWindow, self).__init__(
            procedure_class=CounterTimeseriesProcedure,
            inputs=["n_samples", "sample_rate", "channel", "trigger_source"],
            displays=["n_samples", "sample_rate"],
            x_axis="Time",
            y_axis="Frequency",
            directory_input=True,
            sequencer=True,
            sequencer_inputs=["n_samples", "sample_rate"],
        )
        self.setWindowTitle("Frequency time series")

    def queue(self, *, procedure=None):
        directory = self.directory
        filename = unique_filename(directory, prefix="CNT91")

        if procedure is None:
            procedure = self.make_procedure()
        results = Results(procedure, filename)

        experiment = self.new_experiment(results)

        self.manager.queue(experiment)


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
