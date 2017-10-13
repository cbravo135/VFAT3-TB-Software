import serial
import serial.tools.list_ports


class TtiSerialInterface:

    def __init__(self, baudrate=9600):
        # test which port is the right one by requesting ID.
        self.serial_port = "/dev/ttyACM0"
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            if "PSU" in p.description:
                self.serial_port = p.device
                print self.serial_port

        self.ser = serial.Serial(self.serial_port, baudrate=baudrate, timeout=0.01)


        # Instrument specific commands.
        self.ch1_voltage_req = "V1O?"
        self.ch2_voltage_req = "V2O?"
        self.ch1_current_req = "I1O?"
        self.ch2_current_req = "I2O?"
        self.turn_off_outputs = "OPALL 0"
        self.turn_on_outputs = "OPALL 1"
        self.req_ch1_state = "OP1?"
        self.req_ch2_state = "OP2?"
        self.instrument_identification = "*IDN?"

        self.device_ID = self.req_device_id()

    # Functions

    def execute(self, data):
        self.ser.write(data)
        self.ser.write("\x0A")
        data = self.ser.read(100)  # Read up to 100 bytes
        data = data.rstrip()
        return data

    def read_float(self, command):
        output_data = self.execute(command)
        return_data = float(output_data[:-1])
        return return_data

    def read_int(self, command):
        return int(self.execute(command))

    def req_ch1_current(self):
        return self.read_float(self.ch1_current_req)

    def req_ch2_current(self):
        return self.read_float(self.ch2_current_req)

    def req_ch1_voltage(self):
        return self.read_float(self.ch1_voltage_req)

    def req_ch2_voltage(self):
        return self.read_float(self.ch2_voltage_req)

    def req_device_id(self):
        return self.execute(self.instrument_identification)

    def set_outputs_off(self):
        return self.execute(self.turn_off_outputs)

    def set_outputs_on(self):
        return self.execute(self.turn_on_outputs)

    def req_output_states(self):
        states = [0, 0]
        states[0] = self.read_int(self.req_ch1_state)
        states[1] = self.read_int(self.req_ch2_state)
        return states
#
#
# tti_if = TtiSerialInterface()
# print "Device ID:"
# print tti_if.req_device_id()
# tti_if.set_outputs_on()
# time.sleep(3)
# print "Channel 1 voltage: %.4f" % tti_if.req_ch1_voltage()
# print "Channel 1 current: %.4f" % tti_if.req_ch1_current()
# print "Channel 2 voltage: %.4f" % tti_if.req_ch2_voltage()
# print "Channel 2 current: %.4f" % tti_if.req_ch2_current()
# tti_if.set_outputs_off()
