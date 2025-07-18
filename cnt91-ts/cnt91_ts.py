import logging
import sys
from datetime import datetime, timedelta
from time import sleep

import allantools
import numpy as np
from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows.managed_dock_window import ManagedDockWindow
from pymeasure.experiment import Procedure
from pymeasure.experiment.parameters import (
    FloatParameter,
    IntegerParameter,
    ListParameter,
    Metadata,
)
from pymeasure.instruments.pendulum.cnt91 import (
    CNT91,
    MAX_BUFFER_SIZE,
    MAX_GATE_TIME,
    MIN_BUFFER_SIZE,
    MIN_GATE_TIME,
)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class CounterTimeseriesProcedure(Procedure):
    start_time = Metadata("Start time", default="")

    n_samples = IntegerParameter(
        "Number of samples",
        default=1000,
        minimum=MIN_BUFFER_SIZE,
        maximum=MAX_BUFFER_SIZE,
    )
    gate_time = FloatParameter(
        "Gate time",
        units="s",
        default=1e-3,
        minimum=MIN_GATE_TIME,
        maximum=MAX_GATE_TIME,
    )
    channel = ListParameter(
        "Channel", default="A", choices=["A", "B", "C", "E", "INTREF"]
    )
    trigger_source = ListParameter(
        "Trigger source", default="None", choices=["None", "A", "B", "E"]
    )
    base_freq = FloatParameter(
        "Base Frequency",
        units="Hz",
        minimum=1.0,
        maximum=1e15,
        default=384.230_406_37e12,
    )

    DATA_COLUMNS = ["Time", "Frequency", "Tau", "Allan Deviation"]

    def startup(self):
        log.info("Connecting to Pendulum CNT9x")
        self.counter = CNT91("USB0::0x14EB::0x0091::517306::INSTR")
        self.start_time = datetime.now().isoformat()

    def get_estimates(self):
        duration = self.n_samples * self.gate_time
        estimates = [
            ("Duration / s", f"{duration}"),
            ("Finised at", f"{datetime.now() + timedelta(seconds=duration)}"),
        ]
        return estimates

    def execute(self):
        log.info("Recording time series.")

        duration = self.n_samples * self.gate_time

        trigger_source = self.trigger_source
        if trigger_source == "None":
            log.debug("No trigger source selected.")
            trigger_source = None

        log.info("Start buffering data. Measurement duration is {}s".format(duration))
        buffer_start = datetime.now()
        self.counter.buffer_frequency_time_series(
            self.channel,
            self.n_samples,
            gate_time=self.gate_time,
            trigger_source=trigger_source,
            back_to_back=True,
        )
        log.info("Waiting for data to be buffered")
        while (datetime.now() - buffer_start).total_seconds() < duration:
            self.emit(
                "progress",
                100 * (datetime.now() - buffer_start).total_seconds() / duration,
            )
            sleep(1)

        log.info("Read buffered data")
        freqs = self.counter.read_buffer(n=self.n_samples)
        times = np.linspace(0, duration, num=len(freqs))

        allan_dev = allantools.oadev(
            freqs, rate=1 / self.gate_time, data_type="freq", taus="all"
        )

        # pad with nans so adev data has the same length as the raw data in order to
        # store them in a csv later
        taus = list(allan_dev[0]) + (len(freqs) - len(allan_dev[0])) * [np.nan]
        adev = list(allan_dev[1]) + (len(freqs) - len(allan_dev[1])) * [np.nan]
        adev = np.array(adev) / self.base_freq

        for t, f, tau, ad in zip(times, freqs, taus, adev):

            self.emit(
                "results",
                {"Time": t, "Frequency": f, "Tau": tau, "Allan Deviation": ad},
            )

        if self.should_stop():
            log.warning("Caught the stop flag in the procedure")
            return


class MainWindow(ManagedDockWindow):
    def __init__(self):
        super(MainWindow, self).__init__(
            procedure_class=CounterTimeseriesProcedure,
            inputs=["n_samples", "gate_time", "channel", "trigger_source", "base_freq"],
            displays=["n_samples", "gate_time"],
            x_axis=["Time", "Tau"],
            y_axis=["Frequency", "Allan Deviation"],
            enable_file_input=True,
            sequencer=True,
            sequencer_inputs=["n_samples", "gate_time"],
        )
        self.setWindowTitle("Frequency time series")
        self.filename = r"cnt91-gatetime{Gate time}s"


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
