import logging
from time import sleep

import numpy as np
from ctl200 import laser
from pymeasure.display import Plotter
from pymeasure.experiment import (
    FloatParameter,
    IntegerParameter,
    Procedure,
    Results,
    Worker,
)
from pymeasure.instruments.thorlabs import ThorlabsPM100USB
from pymeasure.log import console_log

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class PICharacteristicsProcedure(Procedure):
    n_steps = IntegerParameter("Number of steps")
    min_current = FloatParameter("Minimum Current", units="mA", default=0)
    max_current = FloatParameter("Maximum Current", units="mA", default=100)
    delay = FloatParameter("Delay", units="s", default=0.1)
    wavelength = FloatParameter("Wavelength", units="nm", default=780)

    DATA_COLUMNS = ["Current", "Power"]

    def startup(self):
        log.info("Connecting to Thorlabs PM100D.")
        self.pm = ThorlabsPM100USB("USB0::0x1313::0x8079::P1001003::INSTR")
        self.pm.wavelength = self.wavelength
        log.info("Connecting to koheron CTL200.")
        self.laser = laser.Laser("COM8")
        self.laser.connect()
        self.laser.laser_status = 0
        self.laser.laser_current = self.min_current
        sleep(self.delay)
        self.laser.laser_status = 1

    def execute(self):
        log.info("Starting the loop with {} steps".format(self.n_steps))
        currents = np.linspace(self.min_current, self.max_current, num=self.n_steps)
        for curr in currents:
            power = self.pm.power
            self.laser.laser_current = curr
            self.emit("results", {"Current": curr, "Power": power})
            log.debug("Emitting results: {}".format(power))
            sleep(self.delay)
            if self.should_stop():
                log.warning("Caught the stop flag in the procedure")
                self.laser.laser_status = 0
                self.laser.close()
                break
        self.laser.laser_status = 0
        self.laser.close()


def main():
    console_log(log)

    log.info("Constructing PICharacteristicsProcedure")
    procedure = PICharacteristicsProcedure()
    procedure.n_steps = 100
    procedure.min_current = 0.0
    procedure.max_current = 100.0

    fn = "example.csv"
    log.info("Constructing the Results with a data file: {}".format(fn))
    results = Results(procedure, fn)

    log.info("Constructing the Plotter")
    plotter = Plotter(results)
    plotter.start()
    log.info("Started the Plotter")

    log.info("Constructing the Worker")
    worker = Worker(results)
    worker.start()
    log.info("Started the Worker")

    log.info("Joining with the worker in at most 20 s.")
    worker.join(timeout=20)
    log.info("Finished the measurement")


if __name__ == "__main__":
    main()
