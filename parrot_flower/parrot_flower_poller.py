""""
Read data from Parrot Flower Power & Pot sensor.
"""

from datetime import datetime, timedelta
from struct import unpack
import logging
from threading import Lock
from btlewrap.base import BluetoothInterface, BluetoothBackendException

# sudo gatttool --device=A0:14:3D:XX:XX:XX --char-desc -a 0x03 --adapter=hci0
# sudo node node_modules/noble/examples/peripheral-explorer.js a0:14:3d:xx:xx:xx
_HANDLE_READ_BATTERY = 0x4B
_HANDLE_READ_VERSION = 0x18
_HANDLE_READ_NAME = 0x03

_HANDLE_READ_TEMPERATURE = 0x44
_HANDLE_READ_MOISTURE = 0x41
_HANDLE_READ_LIGHT = 0x47
_HANDLE_READ_CONDUCTIVITY = 0x31 # ??


P_TEMPERATURE = "temperature"
P_LIGHT = "light"
P_MOISTURE = "moisture"
P_CONDUCTIVITY = "conductivity"
P_BATTERY = "battery"

_LOGGER = logging.getLogger(__name__)


class ParrotFlowerPoller(object):
    """"
    A class to read data from Mi Flora plant sensors.
    """

    def __init__(self, mac, backend, cache_timeout=600, adapter='hci0'):
        """
        Initialize a Mi Flora Poller for the given MAC address.
        """

        self._mac = mac
        self._bt_interface = BluetoothInterface(backend, adapter)
        self._cache = None
        self._cache_timeout = timedelta(seconds=cache_timeout)
        self._last_read = None
        self._fw_last_read = None
        self.ble_timeout = 10
        self.lock = Lock()


    def name(self):
        """Return the name of the sensor."""
        with self._bt_interface.connect(self._mac) as connection:
            name = connection.read_handle(_HANDLE_READ_NAME)  # pylint: disable=no-member

        if not name:
            raise BluetoothBackendException("Could not read data from sensor %s" % self._mac)
        return ''.join(chr(n) for n in name)


    def firmware_version(self):
        """Return the firmware version."""
        with self._bt_interface.connect(self._mac) as connection:
            firmwareRevision = connection.read_handle(_HANDLE_READ_VERSION)  # pylint: disable=no-member

        if not firmwareRevision:
            raise BluetoothBackendException("Could not read data from sensor %s" % self._mac)
        return firmwareRevision.decode("utf-8").split('_')[1].split('-')[1];


    def fill_cache(self):
        """Fill the cache with new data from the sensor."""
        _LOGGER.debug('Filling cache with new sensor data.')
        with self._bt_interface.connect(self._mac) as connection:

            # init cache
            self._cache = {}

            # battery
            battery = connection.read_handle(_HANDLE_READ_BATTERY)  # pylint: disable=no-member
            if not battery:
                raise BluetoothBackendException("Could not read data from sensor %s" % self._mac)
            self._cache[P_BATTERY] = ord(battery)

            # temperature
            temperature = connection.read_handle(_HANDLE_READ_TEMPERATURE)  # pylint: disable=no-member
            if not temperature:
                raise BluetoothBackendException("Could not read data from sensor %s" % self._mac)
            self._cache[P_TEMPERATURE] = round(unpack("<f",temperature)[0], 1)

            # moisture
            moisture = connection.read_handle(_HANDLE_READ_MOISTURE)  # pylint: disable=no-member
            if not moisture:
                raise BluetoothBackendException("Could not read data from sensor %s" % self._mac)
            self._cache[P_MOISTURE] = round(unpack("<f",moisture)[0], 1)

            # light
            light = connection.read_handle(_HANDLE_READ_LIGHT)  # pylint: disable=no-member
            if not light:
                raise BluetoothBackendException("Could not read data from sensor %s" % self._mac)
            self._cache[P_LIGHT] = round(unpack("<f",light)[0], 1)

            # conductivity
            conductivity = connection.read_handle(_HANDLE_READ_CONDUCTIVITY)  # pylint: disable=no-member
            if not conductivity:
                raise BluetoothBackendException("Could not read data from sensor %s" % self._mac)
            self._cache[P_CONDUCTIVITY] = unpack("<H",conductivity)[0]

            _LOGGER.debug('Cache content: %s', "; ".join(["%s=%s" % (key, ('%('+key+')s') % self._cache) for key in self._cache]))
            if self.cache_available():
                self._last_read = datetime.now()
            else:
                # If a sensor doesn't work, wait 5 minutes before retrying
                self._last_read = datetime.now() - self._cache_timeout + \
                    timedelta(seconds=300)


    def parameter_value(self, parameter, read_cached=True):
        """Return a value of one of the monitored paramaters.

        This method will try to retrieve the data from cache and only
        request it by bluetooth if no cached value is stored or the cache is
        expired.
        This behaviour can be overwritten by the "read_cached" parameter.
        """
        # Use the lock to make sure the cache isn't updated multiple times
        with self.lock:
            if (read_cached is False) or \
                    (self._last_read is None) or \
                    (datetime.now() - self._cache_timeout > self._last_read):
                self.fill_cache()
            else:
                _LOGGER.debug("Using cache (%s < %s)",
                              datetime.now() - self._last_read,
                              self._cache_timeout)

        if self.cache_available():
            return self._cache[parameter]
        else:
            raise BluetoothBackendException("Could not read data from sensor %s" % self._mac)


    def clear_cache(self):
        """Manually force the cache to be cleared."""
        self._cache = None
        self._last_read = None


    def cache_available(self):
        """Check if there is data in the cache."""
        return self._cache is not None
