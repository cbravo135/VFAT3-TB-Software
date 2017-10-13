############################################
# Created by Henri Petrow 2017
# Lappeenranta University of Technology
###########################################

from SC_encode import *


class IPbus_response:
    def __init__(self, BCd, data):
        self.type = "IPbus"
        self.BCd = BCd
        # print data
        # print "****************"
        # print "SLOW CONTROL RESPONSE RECEIVED"

        data_in = data[0:8]
        data_in.reverse()
        hdlc_address_bin = ''.join(str(e) for e in data_in)
        if hdlc_address_bin != "":
            self.hdlc_address = int(hdlc_address_bin, 2)
        # print "HDLC Address: %s" % hdlc_address_bin
        # print "HDLC Address: %d" % self.hdlc_address

        data_in = data[8:16]
        data_in.reverse()
        hdlc_control_bin = ''.join(str(e) for e in data_in)
        if hdlc_control_bin != "":
            self.hdlc_control = int(hdlc_control_bin, 2)
        # print "HDLC Control: %s" % hdlc_control_bin
        # print "HDLC Control: %d" % self.hdlc_control

        data_in = data[16:20]
        data_in.reverse()
        info_code_bin = ''.join(str(e) for e in data_in)
        if info_code_bin != "":
            self.info_code = int(info_code_bin, 2)
        # print "Info Code: %s" % info_code_bin
        # print "Info Code: %d" % self.info_code

        data_in = data[20:24]
        data_in.reverse()
        type_ID_bin = ''.join(str(e) for e in data_in)
        self.type_ID = int(type_ID_bin, 2)
        # print "Type Id: %s" % type_ID_bin
        # print "Type Id: %d" % self.type_ID

        data_in = data[24:32]
        data_in.reverse()
        transaction_ID_bin = ''.join(str(e) for e in data_in)
        self.transaction_ID = int(transaction_ID_bin, 2)
        # print "Transaction ID: %s" % transaction_ID_bin
        # print "Transaction ID: %d" % self.transaction_ID

        data_in = data[32:44]
        data_in.reverse()
        words_bin = ''.join(str(e) for e in data_in)
        self.words = int(words_bin, 2)
        # print "Words: %s" % words_bin
        # print "Words: %d" % self.words


        data_in = data[44:48]
        data_in.reverse()
        protocol_bin = ''.join(str(e) for e in data_in)
        self.protocol = int(protocol_bin, 2)
        # print "Protocol: %s" % protocol_bin
        # print "Protocol: %d" % self.protocol

        if self.type_ID == 0:
            if self.words == 5:
                self.data = []
                data_store = data[48:80]
                data_store.reverse()
                self.data.append(data_store)
                data_store = data[80:112]
                data_store.reverse()
                self.data.append(data_store)
                data_store = data[112:144]
                data_store.reverse()
                self.data.append(data_store)
                data_store = data[144:176]
                data_store.reverse()
                self.data.append(data_store)
                data_store = data[176:208]
                data_store.reverse()
                self.data.append(data_store)
            else:
                self.data = data[48:80]
                self.data.reverse()
            # print "Data:"
            # print self.data
        # else:
        #    print "No data."
        # if self.info_code == 0:
        #     print "Transaction ok."
        # else:
        #     print "!-> Transaction error %d ", self.info_code

        if self.info_code != 0:
            print "!-> Transaction error: %d " % self.info_code
            if self.info_code == 1:
                print "IPbus: Bad Header."
            elif self.info_code == 2:
                print "IPbus: Bus Error on Read."
            elif self.info_code == 3:
                print "IPbus: Bus Error on Write."
            elif self.info_code == 4:
                print "IPbus: Bus timeout on Read."
            elif self.info_code == 4:
                print "IPbus: Bus timeout on Write."
            else:
                print "IPbus: Unknown error code"
        crc = []
        for i in data[-16:]: # Invert bits.
            if i == 0:
                crc.append(1)
            elif i == 1:
                crc.append(0)
        received_crc = ''.join(map(str, crc))
        received_crc = int(received_crc,2) # Extract the CRC value from the received message. CRC is the last 16 bits of the data
        crc_data = data[:-16]
        calculated_crc = crc_remainder(crc_data) # Calculate the CRC for the message.
        if received_crc != calculated_crc:
            print "!-> HDLC CRC error."

class datapacket:
    def __init__(self):
        self.type = "data_packet"
        self.header = ""
        self.FIFO_warning = 0
        self.systemBC = 0
        self.EC = ""
        self.ec_size = 0
        self.BC = ""
        self.bc_size = 0
        self.data = ""
        self.szp = 0
        self.partition_table = "" 
        self.spzs_packet = 0
        self.partitions = 0
        self.spzs_data = ""
        self.crc_calc = ""
        self.crc = ""
        self.crc_error = 0
        self.received_crc = 0
        self.calculated_crc = 0
        self.hit_found = 0

    def ready(self, dataformat_register):
        # print "****************"
        # print "DATA PACKET RECEIVED"
        # print "Header: %s" % self.header
        # print "FIFO warning: %d" % self.FIFO_warning
        # print "System BC: %d" % self.systemBC
        # print self.data
        if self.szp == 0:
            if self.EC:
                self.ec_size = len(self.EC)/8
                self.EC = int(self.EC, 2)
                # print "EC: %d" % self.EC
            else:
                #print "No EC value."
                self.EC = 0
            if self.BC:
                self.bc_size = len(self.BC)/8
                self.BC = int(self.BC, 2)
                # print "BC: %d" % self.BC
            else:
                #print "No BC value."
                self.BC = 0

            indices = [i for i, x in enumerate(self.partition_table) if x == "1"]
            indices = indices[:self.partitions]
            if self.spzs_data:
                # print "Decoding SPZS data %s" % self.spzs_data
                for i in range(0, 16):
                    if i in indices:
                        self.data += self.spzs_data[:8]
                        #print "Data found in partition %d, %s" % (i, self.spzs_data[:8])
                        self.spzs_data = self.spzs_data[8:]


                    else:
                        self.data += "00000000"


            if '1' in self.data:
                self.hit_found = 1

            received_crc_int = int(self.crc, 2)
            self.calculated_crc = crc_remainder(list(self.crc_calc[:-16]))

            if received_crc_int != self.calculated_crc:
                self.crc_error = 1
                print("!-> data packet CRC error.")
            else:
                pass
                #print("CRC ok.")


def decode_output_data(filename, register):
    BCcounter = 0

    # Data packet registers
    data_header = 0
    datapacket_status = "IDLE"
    datapacket_byte_counter = 0

    # Slow control registers
    SC_bit_counter = 0
    SC1_counter = 0
    bit_stuffing_flag = 0
    SC_shift_register = [[0, 0]]*8
    SC_shift_register_counter = 0

    # Headers from the chips
    SC0 = "10010110"        # Slow Control 0
    SC1 = "10011001"        # SLow Control 1

    HDR_1 = "00011110"		# Basic Data Packet
    HDR_1W = "01011110"     # Basic Data Packet, With FIFO half full -warning
    HDR_2 = "00011010"		# Zero Suppressed Data Packet
    HDR_2W = "01010110"		# Zero Suppressed Data Packet, With FIFO half full -warning

    # Lists for decoded data
    IPbus_transaction_list = []
    datapacket_list = []
    sync_response_list = []
    transaction_list = []

    hdlc_state = "IDLE"
    hdlc_start_BCd = 0
    hdlc_flag_bit = 0
    hdlc_flag = [0, 1, 1, 1, 1, 1, 1, 0]
    hdlc_data = []
    SC_flag = 0
    flag_nr = 0

    dataformat_register = register[130] 
    FPGA_output = []
    with open(filename, 'r') as f:
        for line in f:
            # print line
            line = line.rstrip('\n')
            line = line.replace(" ", "")
            split_line = line.split(",")

            # Calculate the datapacket size
            if dataformat_register.ECb[0] == 0 or dataformat_register.ECb[0] == 3:
                EC_size = 1
            if dataformat_register.ECb[0] == 1:
                EC_size = 2
            if dataformat_register.ECb[0] == 2:
                EC_size = 3
            if dataformat_register.BCb[0] == 0:
                BC_size = 2
            if dataformat_register.BCb[0] == 1:
                BC_size = 3
            if dataformat_register.TT[0] == 1:
                BC_size = 0                
            if dataformat_register.TT[0] == 2:
                EC_size = 0

            try:
                BCd = int(split_line[0])
            except Exception as e: 
                print(e)
                print "-IGNORE: Invalid value: %s" % split_line[0]
                continue
            # print [i[1] for i in SC_shift_register]
            # print hdlc_state
            input_value = split_line[1]
            # FPGA_output.append(input_value)
            # print input_value
            # print hdlc_flag_bit
            BCcounter = BCcounter + BCd
            # print datapacket_status
            # Sync responses.
            if input_value == "00111010":
                sync_response_list.append([BCcounter, "SyncAck"])
                # print "******Sync Ack********"
            if input_value == "11111110":
                sync_response_list.append([BCcounter, "VerifAck"])
                # print "******SyncVerifAck********"

            # DATA PACKETS
            # print ""
            # print "Reading line: %s" % input_value
            # print "datapacket byte counter: %d" % datapacket_byte_counter
            if datapacket_status != "IDLE":
                # print input_value
                #data_packet.crc_calc += input_value[::-1]
                data_packet.crc_calc += input_value

            if (input_value == HDR_1 or input_value == HDR_1W) and datapacket_status == "IDLE": # See if the read line is Header 1.
                # print("Header I found.")
                data_header = 1                               # Type of header. To be used to stop after EC or BC.
                data_packet = datapacket()                    # Create a new data packet object.
                data_packet.crc_calc += input_value
                # print input_value
                if input_value == HDR_1W:                     # Check if FIFO warning was given.
                    data_packet.FIFO_warning = 1              # Set the FIFO warning to the object.
                data_packet.header = input_value              # Set the binary header to the new object.
                data_packet.systemBC = BCcounter              # Set the system BC counter to the object. Tells the time of arrival of the packet.
                if EC_size == 0:                              # If size of EC counter is zero, the status is changed straight to BC.
                    datapacket_status = "BC"
                else:
                    datapacket_status = "EC"                  # If EC counter size is not zero, we change the status to EC
                datapacket_byte_counter = 0                   # Set byte counter to zero. This is used to count the number of bytes to be read in different stages.

            elif (input_value == HDR_2 or input_value == HDR_2W) and datapacket_status == "IDLE":
                # print("Header II found.")
                data_header = 2                               # Type of header.
                data_packet = datapacket()                    # Create a new data packet object.
                data_packet.crc_calc += input_value
                # print input_value
                if input_value == HDR_2W:                     # Check if FIFO warning was given.
                    data_packet.FIFO_warning = 1              # Set the FIFO warning to the object.
                data_packet.header = input_value              # Set the binary header to the new object.
                data_packet.systemBC = BCcounter              # Set the system BC counter to the object. Tells the time of arrival of the packet.
                if dataformat_register.SZP[0] == 1:           # If SZP has been set to one. We only receive the header, so data packet is ready.
                    data_packet.szp = 1
                    data_packet.ready(dataformat_register)    # Finish the data_packet object.
                    datapacket_list.append(data_packet)       # Add the finished data packet to the data packet list.
                    transaction_list.append(data_packet)
                    continue                                  # Continue to read next line from file.
                if dataformat_register.SZD[0] == 1:           # If SZD is set to one, we will get also time tag
                    if EC_size == 0:                          # If size of EC is 0, only BC is received. The state is changed straight to BC
                        datapacket_status = "BC"
                    else:
                        datapacket_status = "EC"              # If the size of the EC counter is not zero. Status is set to EC to collect the EC counter data.
                datapacket_byte_counter = 0                   # Set byte counter to zero. This is used to count number of bytes to be read in different stages.

            elif datapacket_status == "EC":                   # Enter the EC to collect the bytes for EC.e
                data_packet.EC += input_value                 # Input value is added to the EC value. 
                datapacket_byte_counter += 1                  # Byte counter is incremented by one to count the amount of EC bytes.
                if datapacket_byte_counter >= EC_size:        # If byte counter is >= than size of EC we have all EC bytes and we can move to next state.
                    if BC_size:                               # If time tag format is 0 or 3 we have EC+BC. So we move to state BC to get also BC counter.
                        datapacket_status = "BC"
                    elif data_header == 2:                      # If header was 2 there is no data after BC
                        datapacket_status = "CRC"             # Stop data collection by setting status to IDLE.
                    else:
                        datapacket_status = "DATA"            # Else we only have EC so we can move to collect the data.
                    datapacket_byte_counter = 0               # Set the byte counter to 0 for the next state.

            elif datapacket_status == "BC":                   # Enter the BC to collect the bytes for BC.
                data_packet.BC += input_value                 # Input value is added to the EC value.  
                datapacket_byte_counter += 1                  # Byte counter is incremented by one to count the amount of BC bytes.
                if datapacket_byte_counter >= BC_size:        # If byte counter is >= than size of BC we have all BC bytes and we can move to next state.
                    if data_header == 2:                      # If header was 2 there is no data after BC
                        datapacket_status = "CRC"             # Stop data collection by setting status to IDLE.
                    else:
                        datapacket_status = "DATA"            # Set state to DATA 
                    datapacket_byte_counter = 0               # Set the byte counter to 0 for the next state.

            elif datapacket_status == "DATA" and dataformat_register.DT[0] == 1:  # Enter the DATA state to collect the bytes for DATA.
                # print "Collecting SPZS Data"
                if len(data_packet.partition_table) < 16:
                    # print "Collecting Partition table %s" % input_value
                    data_packet.partition_table += input_value
                elif len(data_packet.partition_table) == 16:
                    if datapacket_byte_counter == 0:
                        data_packet.spzs_packet = 1
                        data_size = sum(int(x) for x in data_packet.partition_table if x.isdigit())
                        if data_size > dataformat_register.PAR[0]+1:
                            data_size = dataformat_register.PAR[0]+1
                        if dataformat_register.P16[0] == 1:
                            datapacket_status = "CRC"         # Set state to IDLE.
                        data_packet.partitions = data_size
                        # print "The data size is: %d" % data_size

                    # print "SPZS data: %s" % input_value
                    data_packet.spzs_data += input_value      # Input value is added to the data
                    datapacket_byte_counter += 1              # Byte counter is incremented by one to count the amount of data bytes.
                    if datapacket_byte_counter >= data_size:      # If byte counter is >= than data_size we have all data bytes and we can move to next state.
                        datapacket_status = "CRC"                 # Set state to IDLE.
                        datapacket_byte_counter = 0               # Set the byte counter to 0 for the next state.

            elif datapacket_status == "DATA" and dataformat_register.DT[0] == 0: # Enter the DATA state to collect the bytes for DATA.
                data_size = 16
                # print "Collecting data: %s" % input_value
                data_packet.data += input_value                # Input value is added to the data.               
                datapacket_byte_counter += 1                   # Byte counter is incremented by one to count the amount of data bytes. 
                if datapacket_byte_counter >= data_size:       # If byte counter is >= than data_size we have all data bytes and we can move to next state.
                    datapacket_status = "CRC"                  # Set state to IDLE.
                    datapacket_byte_counter = 0                # Set the byte counter to 0 for the next state.

            elif datapacket_status == "CRC":                   # Enter the DATA state to collect the bytes for DATA.
                crc_size = 2
                # print "Collecting CRC."
                data_packet.crc += input_value                 # Input value is added to the data.               
                datapacket_byte_counter += 1                   # Byte counter is incremented by one to count the amount of data bytes. 
                if datapacket_byte_counter >= crc_size:        # If byte counter is >= than data_size we have all data bytes and we can move to next state.
                    data_packet.ready(dataformat_register)
                    datapacket_list.append(data_packet)        # Add the finished data packet to the data packet list
                    transaction_list.append(data_packet)
                    datapacket_status = "IDLE"                 # Set state to IDLE.
                    datapacket_byte_counter = 0                # Set the byte counter to 0 for the next state.

            # SLOW CONTROL

            if input_value == SC0:
                # print "SC0"
                if SC1_counter == 5 and hdlc_state == "DATA":
                    # print "Bit stuffing detected, Ignoring one SC0."
                    # FPGA_output.append("Bit stuffing.")
                    SC1_counter = 0
                    if SC_bit_counter != 0:
                        bit_stuffing_flag = 1

                else:
                    SC_shift_register = SC_shift_register[1:]
                    SC_shift_register.append([BCcounter, 0])
                    SC_bit_counter += 1
                    SC1_counter = 0
                    SC_flag = 1
                
            if input_value == SC1:
                # print "SC1"
                SC1_counter += 1
                SC_shift_register = SC_shift_register[1:]
                SC_shift_register.append([BCcounter, 1])
                SC_bit_counter += 1
                SC_flag = 1

            if SC_flag == 1:
                if [i[1] for i in SC_shift_register] == hdlc_flag and bit_stuffing_flag == 0 and flag_nr < 2:
                    if hdlc_flag_bit == 0:
                        hdlc_start_BCd = SC_shift_register[0][0]
                        # FPGA_output.append("Start flag")
                        hdlc_state = "DATA"
                        # print 'HDLC flag found, start collecting data.'
                        SC_bit_counter = 0
                        flag_nr += 1
                        SC_shift_register = [[0, 0]]*8

                if SC_bit_counter == 8 and hdlc_state == "DATA":
                    if [i[1] for i in SC_shift_register] == hdlc_flag and bit_stuffing_flag == 0:
                        # FPGA_output.append("Stop flag")
                        # print 'HDLC flag found, stop collecting data. Analysing data..'
                        hdlc_flag_bit = 0
                        if len(hdlc_data) >= 63:
                            new_IPbus_packt = IPbus_response(hdlc_start_BCd, hdlc_data)
                            IPbus_transaction_list.append(new_IPbus_packt)
                            transaction_list.append(new_IPbus_packt)
                        else:
                            # FPGA_output.append("Too Short:%d." % len(hdlc_data))
                            print "Too short."
                        hdlc_state = "IDLE"
                        SC_bit_counter = 0
                        bit_stuffing_flag = 0
                        del hdlc_data[:]
                        flag_nr = 0
                        SC_shift_register = [[0, 0]] * 8
                    else:
                        # print 'Collecting a byte of SC data: %s' % str([i[1] for i in SC_shift_register])
                        hdlc_flag_bit = 1
                        hdlc_data.extend([i[1] for i in SC_shift_register])
                        SC_bit_counter = 0
                        bit_stuffing_flag = 0
                        flag_nr = 0
                        SC_shift_register = [[0, 0]] * 8

                SC_flag = 0

    output_data = [IPbus_transaction_list, datapacket_list, sync_response_list, transaction_list,FPGA_output]
    return output_data
