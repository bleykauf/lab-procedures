from datetime import datetime
from time import sleep

import pandas as pd
from meer_tec import TEC, USB
from pymeasure.instruments.thorlabs import ThorlabsPM100USB


def main():

    # Connect to the power meter
    pm = ThorlabsPM100USB("USB0::0x1313::0x8078::P0032734::INSTR")
    usb = USB("COM17")
    tec = TEC(usb, 0)

    i = -1
    while True:
        i += 1
        sleep(1)

        data = {
            "time": [datetime.now()],
            "power": [pm.power],
            "t_heater": [tec.object_temperature],
            "t_cell": [tec.sink_temperature],
        }

        print(data)

        df = pd.DataFrame(data)
        if i == 0:
            df.to_csv("data.csv", index=False)
        else:
            df.to_csv("data.csv", mode="a", header=False, index=False)


if __name__ == "__main__":
    main()
