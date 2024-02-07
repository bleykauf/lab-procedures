import logging
import pickle
import sys

from linien_client.connection import LinienClient
from pymeasure.display.Qt import QtGui
from pymeasure.display.windows import ManagedWindow
from pymeasure.experiment import Procedure, Results
from pymeasure.experiment.results import unique_filename

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class LinienSpectrumProcedure(Procedure):

    DATA_COLUMNS = ["Index", "Error Signal", "Monitor Signal"]

    def startup(self):
        log.info("Connecting to RedPitaya")
        self.client = LinienClient(
            {"host": "rp-f012ba.local", "username": "root", "password": "root"},
            autostart_server=False,
        )

    def execute(self):
        log.info("Taking the spectrum.")

        to_plot = pickle.loads(self.client.parameters.to_plot.value)
        error_signal = to_plot["error_signal_1"]
        monitor_signal = to_plot["monitor_signal"]
        index = range(len(monitor_signal))

        for i in index:

            es = error_signal[i]
            ms = monitor_signal[i]

            self.emit(
                "results",
                {
                    "Index": i,
                    "Error Signal": es,
                    "Monitor Signal": ms,
                },
            )

        if self.should_stop():
            log.warning("Caught the stop flag in the procedure")
            self.client.disconnect()
            return

        self.client.disconnect()


class MainWindow(ManagedWindow):
    def __init__(self):
        super(MainWindow, self).__init__(
            procedure_class=LinienSpectrumProcedure,
            x_axis="Index",
            y_axis="Error Signal",
            directory_input=True,
        )
        self.setWindowTitle("Take Linien Spectrum")

    def queue(self):
        directory = self.directory
        filename = unique_filename(directory, prefix="LINIEN")

        procedure = self.make_procedure()
        results = Results(procedure, filename)
        experiment = self.new_experiment(results)

        self.manager.queue(experiment)


def main():
    app = QtGui.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
