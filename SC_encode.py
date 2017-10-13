############################################
# Created by Henri Petrow 2017
# Lappeenranta University of Technology
###########################################

from test_system_functions import *


class SC_encode:

    def __init__(self):
        self.SC0 = "SC0"
        self.SC1 = "SC1"
        self.transaction_ID = 0

    def update_trans_ID(self):
        self.transaction_ID += 1
        if self.transaction_ID > 255:
            self.transaction_ID = 0
        return self.transaction_ID

    def binary_to_sc(self, package):
        package = [self.SC1 if x == 1 else x for x in package]
        package = [self.SC0 if x == 0 else x for x in package]
        return package

    def create_SC_packet(self, address, data, action, BCcounter, nr_words = 5):
        if action == "IDLE":
            action_value = "f"
            words = 1
        if action == "READ":
            action_value = 0
            words = 1
        if action == "MULTI_READ":
            action_value = 0
            words = 5
        if action == "MULTI_WRITE":
            action_value = 1
            words = nr_words
        if action == "WRITE":
            words = 1
            action_value = 1
        self.transaction_ID = self.update_trans_ID()
        ipbus = self.IPbus14_package(address, data, words, action_value, self.transaction_ID)
        paketti = self.HDLC_package(ipbus)
        paketti = self.binary_to_sc(paketti)  # Convert binary form to a list of SC0 and SC1 commands
        if BCcounter != 0:
            with open("./data/sent_SCs.dat", "a") as myfile:
                myfile.write("%d %s\n" % (BCcounter, self.transaction_ID))
        return [paketti, self.transaction_ID]

    def HDLC_package(self, ipbus_package):
        hdlc_pack = []
        data = []
        flag = [0, 1, 1, 1, 1, 1, 1, 0]
        address = [0, 0, 0, 0, 0, 0, 0, 0]
        control = [1, 1, 0, 0, 0, 0, 0, 0]

        data.extend(address)
        data.extend(control)
        data.extend(ipbus_package)
        crc = crc_remainder(data)
        crc_bin = bin(crc)
        crc_bin = crc_bin[2:]
        crc_len = len(crc_bin)
        crc_bin = (16-crc_len)*'0' + crc_bin
        crc_bin = list(crc_bin)
        crc_bin = [int(i) for i in crc_bin]
        #crc_bin.reverse()
        crc = []
        for i in crc_bin:
            if i == 0:
                crc.append(1)
            elif i == 1:
                crc.append(0)
        data.extend(crc)
        data = data_packet_bit_stuffing(data)


        hdlc_pack.extend(flag)
        hdlc_pack.extend(data)
        hdlc_pack.extend(flag)
        return hdlc_pack

    def IPbus14_package(self, addr, data, wrds, typ, trans_ID):
        ipbus_pack = []
        
        # Protocol Version. 0x2
        protocol_version = [0, 1, 0, 0]
        
        # Info code 0xe
        info_code = [1, 1, 1, 1]
        
        # Number of words. 12 bits.
        words = dec_to_bin_with_stuffing(wrds, 12)
        words.reverse()



        # Transaction_ID. 8 bits.
        transaction_ID = dec_to_bin_with_stuffing(trans_ID, 8)
        transaction_ID.reverse()

        ipbus_pack.extend(info_code)

        filler_16bits = [0]*16

        # Address. 32 bits.
        address = dec_to_bin_with_stuffing(addr, 32)
        address.reverse()

        # Data. 32 bits.
        # data = dec_to_bin_with_stuffing(data, 32)
     

        if typ == "f": # Idle
            type_ID = [1, 1, 1, 1]
            ipbus_pack.extend(type_ID)
            ipbus_pack.extend(transaction_ID)
            words = dec_to_bin_with_stuffing(0, 12)
            ipbus_pack.extend(words)
            ipbus_pack.extend(protocol_version)
  
        if typ == 0: # Read
            type_ID = [0, 0, 0, 0]
            ipbus_pack.extend(type_ID)
            ipbus_pack.extend(transaction_ID)
            ipbus_pack.extend(words)
            ipbus_pack.extend(protocol_version)
            ipbus_pack.extend(address)

        if typ == 1: # Write
            type_ID = [1, 0, 0, 0]
            ipbus_pack.extend(type_ID)
            ipbus_pack.extend(transaction_ID)
            ipbus_pack.extend(words)
            ipbus_pack.extend(protocol_version)
            ipbus_pack.extend(address)
            if wrds == 1:
                ipbus_pack.extend(data)
                ipbus_pack.extend(filler_16bits)
            else:
                ipbus_pack.extend(data)                
            
        if typ == 2: # Non-incrementing Read
            type_ID = [0, 1, 0, 0]
            ipbus_pack.extend(type_ID)
            ipbus_pack.extend(transaction_ID)
            ipbus_pack.extend(address)
            
        if typ == 3: # Non-incrementing Write 
            type_ID = [1,1,0,0]
        if typ == 4: # Read-Modify-Write bits
            type_ID = [0,0,1,0]
        if typ == 5: # Read-Modify-Write sum
            type_ID = [1,0,1,0]
            
        return ipbus_pack

