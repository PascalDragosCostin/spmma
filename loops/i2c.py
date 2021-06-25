import threading

from misc.message import MessageType
from misc.message import ButtonType

from modules.bme import BME280
from modules.adc import ADC
from modules.ltr import LTR_Wrapper


PROXIMTY_SLEEP_TRESHOLD = 1500
PROXIMTY_NEXT_TRESHOLD = 100

# exista 2 threaduri care acceseaza LTR
# sincronizare cu semafoare
lock = threading.Lock()

# Producer 1
def i2c_loop(q):
    try:
        bme280 = BME280()
        bme280.set_operation_mode(operation_mode="weather")
        adc = ADC()
        ltr = LTR_Wrapper()

        button_delay = 0.1  # seconds
        button_debounce = 2 # seconds
        read_delay = 0.1  # seconds

        button_thread(q, ltr, button_delay, button_debounce)
        sensor_thread(q, bme280, adc, ltr, read_delay)

        while(True):
            pass

    except KeyboardInterrupt:
        print("I2C loop stops...")


def button_thread(q, ltr, button_delay, button_debounce):
    lock.acquire()
    proximity = ltr.get_proximity()
    lock.release()
    if proximity > PROXIMTY_SLEEP_TRESHOLD:
        q.put((MessageType.BTN_MESSAGE, ButtonType.SLEEP))
        # dau mesaj sa afisez alta valoare pe ecran
        t = threading.Timer(button_debounce, button_thread, [q, ltr, button_delay, button_debounce])
        t.daemon = True
        t.start()
    elif proximity > PROXIMTY_NEXT_TRESHOLD:
        q.put((MessageType.BTN_MESSAGE, ButtonType.NEXT))
        t = threading.Timer(button_debounce, button_thread, [q, ltr, button_delay, button_debounce])
        t.daemon = True
        t.start()
    else:
        t = threading.Timer(button_delay, button_thread, [q, ltr, button_delay, button_debounce])
        t.daemon = True
        t.start()


def sensor_thread(q, bme280, adc, ltr, read_delay):
    weather_parameters = bme280.read_and_get_parameters()
    weather_parameters['rt'] = adc.read_temp()

    ox = adc.read_OX()
    red = adc.read_RED()
    nh3 = adc.read_NH3()
    gases = {"ox": ox, "red": red, "nh3": nh3}

    lock.acquire()
    lux = ltr.get_lux_auto_range()
    proximity = ltr.get_proximity()
    lock.release()

    weather_parameters['t'] = round(weather_parameters['t'], 2)
    weather_parameters['rt'] = round(weather_parameters['rt'], 2)
    weather_parameters['p'] = round(weather_parameters['p'], 4)
    weather_parameters['h'] = round(weather_parameters['h'], 2)

    for k, v in gases.items():
        gases[k] = round(v, 0)
    lux = round(lux, 2)

    i2c_object = (weather_parameters, gases, lux, proximity)

    q.put((MessageType.I2C_MESSAGE, i2c_object))

    # print(i2c_object)

    t = threading.Timer(read_delay, sensor_thread, [
                        q, bme280, adc, ltr, read_delay])
    t.daemon = True
    t.start()


# Pentru testare
if __name__ == "__main__":
    import multiprocessing
    q = multiprocessing.Queue()
    i2c_loop(q)