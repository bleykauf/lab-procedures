import logging
import sys

from pymeasure.display.Qt import QtWidgets
from pymeasure.display.windows.managed_dock_window import ManagedDockWindow
from pymeasure.experiment import Procedure
from pymeasure.experiment.parameters import BooleanParameter, IntegerParameter
from pymeasure.instruments.lecroy.lecroyT3DSO1204 import LeCroyT3DSO1204

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class ScopeReadoutProcedure(Procedure):

    DATA_COLUMNS = ["Time", "CH1", "CH2", "CH3", "CH4"]

    ch1 = BooleanParameter("CH1", default=True)
    ch2 = BooleanParameter("CH2", default=False)
    ch3 = BooleanParameter("CH3", default=False)
    ch4 = BooleanParameter("CH4", default=False)

    requested_points = IntegerParameter(
        "Requested Points", default=0, units="pts", minimum=0, maximum=175000
    )
    sparsing = IntegerParameter("Sparsing", default=1000, minimum=1, maximum=10000)

    def startup(self):
        self.scope = LeCroyT3DSO1204("TCPIP::192.168.123.158::INSTR")

    def execute(self):
        requested_channels = []
        for i, request in enumerate([self.ch1, self.ch2, self.ch3, self.ch4]):
            if request:
                requested_channels.append(f"CH{i + 1}")

        wfs = {}
        for ch in requested_channels:
            log.info(f"Downloading waveform for {ch}")
            wf, ts, _ = self.scope.download_waveform(
                ch, requested_points=self.requested_points, sparsing=self.sparsing
            )
            wfs[ch] = wf

        for i, t in enumerate(ts):
            self.emit("results", {"Time": t, **{ch: wfs[ch][i] for ch in wfs}})

        if self.should_stop():
            log.warning("Caught the stop flag in the procedure")
            return


class MainWindow(ManagedDockWindow):
    def __init__(self):
        super(MainWindow, self).__init__(
            procedure_class=ScopeReadoutProcedure,
            inputs=["requested_points", "sparsing", "ch1", "ch2", "ch3", "ch4"],
            displays=["requested_points", "sparsing"],
            x_axis="Time",
            y_axis=["CH1", "CH2", "CH3", "CH4"],
            enable_file_input=True,
        )
        self.setWindowTitle("Scope Readout")


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
