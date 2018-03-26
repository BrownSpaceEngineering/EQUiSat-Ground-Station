from struct import unpack
from binascii import unhexlify
import json

def get_bit(byte,i):
    return 1 if ((byte&(1<<i))!=0) else  0

def hex_to_int_le(hexstr):
	return unpack('<i', unhexlify(hexstr))[0]

def left_shift_8(byte):
	return byte << 8

def hex_string_byte_to_signed_int(byte):
	return int(byte + '000000') >> 24

def parse_preamble(ps):
	preamble = {}
	preamble['callsign'] = ps[0:12].decode("hex")
	preamble['timestamp'] = hex_to_int_le(ps[12:20])
	msg_op_states = int(ps[20:22],16)
	preamble['message_type'] = str(get_bit(msg_op_states, 7))+str(get_bit(msg_op_states, 6))+str(get_bit(msg_op_states, 5))
	preamble['satellite_state'] = str(get_bit(msg_op_states, 4))+str(get_bit(msg_op_states, 3))+str(get_bit(msg_op_states, 2))
	preamble['SPF_ST'] = str(get_bit(msg_op_states, 1))
	preamble['MRAM_CPY'] = str(get_bit(msg_op_states, 0))
	preamble['bytes_of_data'] = int(ps[22:24], 16)	
	preamble['num_errors'] = int(ps[24:26], 16)	
	return preamble

def parse_current_info(ps):
	current_info = {}
	current_info['time_to_flash'] = int(ps[26:28], 16)
	current_info['boot_count'] = int(ps[28:30], 16)
	current_info['L1_REF'] = left_shift_8(int(ps[30:32], 16))
	current_info['L2_REF'] = left_shift_8(int(ps[32:34], 16))
	current_info['L1_SNS'] = left_shift_8(hex_string_byte_to_signed_int(ps[34:36]))
	current_info['L2_SNS'] = left_shift_8(hex_string_byte_to_signed_int(ps[36:38]))
	current_info['L1_TEMP'] = left_shift_8(hex_string_byte_to_signed_int(ps[38:40]))
	current_info['L2_TEMP'] = left_shift_8(hex_string_byte_to_signed_int(ps[40:42]))
	current_info['PANELREF'] = left_shift_8(int(ps[42:44], 16))
	current_info['L_REF'] = left_shift_8(int(ps[44:46], 16))
	
	bat_digsigs_1 = int(ps[46:48],16)
	bat_digsigs_2 = int(ps[48:50],16)

	current_info['L1_RUN_CHG'] = str(get_bit(bat_digsigs_1, 7))
	current_info['L2_RUN_CHG'] = str(get_bit(bat_digsigs_1, 6))
	current_info['LF_B1_RUN_CHG'] = str(get_bit(bat_digsigs_1, 5))
	current_info['LF_B2_RUN_CHG'] = str(get_bit(bat_digsigs_1, 4))
	current_info['LF_B2_CHGN'] = str(get_bit(bat_digsigs_1, 3))
	current_info['LF_B2_FAULTN'] = str(get_bit(bat_digsigs_1, 2))
	current_info['LF_B1_FAULTN'] = str(get_bit(bat_digsigs_1, 1))
	current_info['LF_B0_FAULTN'] = str(get_bit(bat_digsigs_1, 0))

	current_info['L2_ST'] = str(get_bit(bat_digsigs_2, 7))
	current_info['L1_ST'] = str(get_bit(bat_digsigs_2, 6))
	current_info['L1_DISG'] = str(get_bit(bat_digsigs_2, 5))
	current_info['L2_DISG'] = str(get_bit(bat_digsigs_2, 4))
	current_info['L1_CHGN'] = str(get_bit(bat_digsigs_2, 3))
	current_info['L1_FAULTN'] = str(get_bit(bat_digsigs_2, 3))
	current_info['L2_CHGN'] = str(get_bit(bat_digsigs_2, 2))
	current_info['L2_FAULTN'] = str(get_bit(bat_digsigs_2, 1))

	current_info['LF1REF'] = left_shift_8(int(ps[50:52], 16))
	current_info['LF2REF'] = left_shift_8(int(ps[52:54], 16))
	current_info['LF3REF'] = left_shift_8(int(ps[54:56], 16))
	current_info['LF4REF'] = left_shift_8(int(ps[56:58], 16))
	
	return current_info

def parse_attitude_data(ps):
	data = []
	for i in range(0,5):
		cur = {}
		start = 58
		cur['IR_FLASH_OBJ'] = hex_to_int_le(ps[start:start+4]+'0000')*0.02 - 273.15
		cur['IR_SIDE1_OBJ'] = hex_to_int_le(ps[start+4:start+8]+'0000')*0.02 - 273.15
		cur['IR_SIDE2_OBJ'] = hex_to_int_le(ps[start+8:start+12]+'0000')*0.02 - 273.15
		cur['IR_RBF_OBJ'] = hex_to_int_le(ps[start+12:start+16]+'0000')*0.02 - 273.15
		cur['IR_ACCESS_OBJ'] = hex_to_int_le(ps[start+16:start+20]+'0000')*0.02 - 273.15
		cur['IR_TOP1_OBJ'] = hex_to_int_le(ps[start+20:start+24]+'0000')*0.02 - 273.15

		pd_1 = int(ps[start+24:start+26],16)
		pd_2 = int(ps[start+26:start+28],16)

		cur['PD_FLASH'] = str(get_bit(pd_1, 7))+str(get_bit(pd_1, 6))
		cur['PD_SIDE1'] = str(get_bit(pd_1, 5))+str(get_bit(pd_1, 4))
		cur['PD_SIDE2'] = str(get_bit(pd_1, 3))+str(get_bit(pd_1, 2))
		cur['PD_ACCESS'] = str(get_bit(pd_1, 1))+str(get_bit(pd_1, 0))

		cur['PD_TOP1'] = str(get_bit(pd_2, 7))+str(get_bit(pd_2, 6))
		cur['PD_TOP2'] = str(get_bit(pd_2, 5))+str(get_bit(pd_2, 4))

		accelerometer = {}
		accelerometer['x'] = left_shift_8(int(ps[start+28:start+30], 16))
		accelerometer['y'] = left_shift_8(int(ps[start+30:start+32], 16))
		accelerometer['z'] = left_shift_8(int(ps[start+32:start+34], 16))
		cur['accelerometer'] = accelerometer

		gyroscope = {}
		gyroscope['x'] = left_shift_8(int(ps[start+34:start+36], 16))
		gyroscope['y'] = left_shift_8(int(ps[start+36:start+38], 16))
		gyroscope['z'] = left_shift_8(int(ps[start+38:start+40], 16))
		cur['gyroscope'] = gyroscope

		magnetometer = {}
		magnetometer['x'] = left_shift_8(int(ps[start+40:start+42], 16))
		magnetometer['y'] = left_shift_8(int(ps[start+42:start+44], 16))
		magnetometer['z'] = left_shift_8(int(ps[start+44:start+46], 16))
		cur['magnetometer'] = magnetometer

		cur['timestamp'] = hex_to_int_le(ps[start+46:start+54])

		data.append(cur)
		start += 54	
	return data

def parse_idle_data(ps):
	data = []
	for i in range(0,7):
		cur = {}
		start = 58
		
		event_history = int(ps[start:start+2],16)
		cur['ANTENNA_DEPLOYED'] = str(get_bit(event_history, 7))
		cur['LION_1_CHARGED'] = str(get_bit(event_history, 6))
		cur['LION_2_CHARGED'] = str(get_bit(event_history, 5))
		cur['LIFEPO4_B1_CHARGED'] = str(get_bit(event_history, 4))
		cur['LIFEPO4_B2_CHARGED'] = str(get_bit(event_history, 3))
		cur['FIRST_FLASH'] = str(get_bit(event_history, 2))
		cur['PROG_MEM_REWRITTEN'] = str(get_bit(event_history, 1))

		current_info['L1_REF'] = left_shift_8(int(ps[start+2:start+4], 16))
		current_info['L2_REF'] = left_shift_8(int(ps[start+4:start+6], 16))
		current_info['L1_SNS'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+6:start+8]))
		current_info['L2_SNS'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+8:start+10]))
		current_info['L1_TEMP'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+10:start+12]))
		current_info['L2_TEMP'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+12:start+14]))
		current_info['PANELREF'] = left_shift_8(int(ps[start+14:start+16], 16))
		current_info['L_REF'] = left_shift_8(int(ps[start+16:start+18], 16))

		bat_digsigs_1 = int(ps[start+18:start+20],16)
		bat_digsigs_2 = int(ps[start+20:start+22],16)

		current_info['L1_RUN_CHG'] = str(get_bit(bat_digsigs_1, 7))
		current_info['L2_RUN_CHG'] = str(get_bit(bat_digsigs_1, 6))
		current_info['LF_B1_RUN_CHG'] = str(get_bit(bat_digsigs_1, 5))
		current_info['LF_B2_RUN_CHG'] = str(get_bit(bat_digsigs_1, 4))
		current_info['LF_B2_CHGN'] = str(get_bit(bat_digsigs_1, 3))
		current_info['LF_B2_FAULTN'] = str(get_bit(bat_digsigs_1, 2))
		current_info['LF_B1_FAULTN'] = str(get_bit(bat_digsigs_1, 1))
		current_info['LF_B0_FAULTN'] = str(get_bit(bat_digsigs_1, 0))

		current_info['L2_ST'] = str(get_bit(bat_digsigs_2, 7))
		current_info['L1_ST'] = str(get_bit(bat_digsigs_2, 6))
		current_info['L1_DISG'] = str(get_bit(bat_digsigs_2, 5))
		current_info['L2_DISG'] = str(get_bit(bat_digsigs_2, 4))
		current_info['L1_CHGN'] = str(get_bit(bat_digsigs_2, 3))
		current_info['L1_FAULTN'] = str(get_bit(bat_digsigs_2, 3))
		current_info['L2_CHGN'] = str(get_bit(bat_digsigs_2, 2))
		current_info['L2_FAULTN'] = str(get_bit(bat_digsigs_2, 1))

		current_info['RAD_TEMP'] = left_shift_8(int(ps[start+22:start+24], 16))
		current_info['IMU_TEMP'] = left_shift_8(int(ps[start+24:start+26], 16))

		current_info['IR_FLASH_AMB'] = left_shift_8(int(ps[start+26:start+28], 16))*0.02 - 273.15
		current_info['IR_SIDE1_AMB'] = left_shift_8(int(ps[start+28:start+30], 16))*0.02 - 273.15
		current_info['IR_SIDE2_AMB'] = left_shift_8(int(ps[start+30:start+32], 16))*0.02 - 273.15
		current_info['IR_RBF_AMB'] = left_shift_8(int(ps[start+32:start+34], 16))*0.02 - 273.15
		current_info['IR_ACCESS_AMB'] = left_shift_8(int(ps[start+34:start+36], 16))*0.02 - 273.15
		current_info['IR_TOP1_AMB'] = left_shift_8(int(ps[start+36:start+38], 16))*0.02 - 273.15

		cur['timestamp'] = hex_to_int_le(ps[start+38:start+46])

		data.append(cur)
		start += 46	
	return data

def parse_flash_burst_data(ps):
	data = []
	for i in range(0,1):
		cur = {}
		start = 58
		cur['LED1TEMP'] = left_shift_8(hex_string_byte_to_signed_int(ps[start:start+2]))
		cur['LED2TEMP'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+2:start+4]))
		cur['LED3TEMP'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+4:start+6]))
		cur['LED4TEMP'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+6:start+8]))
		cur['LF1_TEMP'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+8:start+10]))
		cur['LF3_TEMP'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+10:start+12]))
		cur['LFB1SNS'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+12:start+14]))
		cur['LFB1OSNS'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+14:start+16]))	
		cur['LFB2SNS'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+16:start+18]))
		cur['LFB2OSNS'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+18:start+20]))

		cur['LF1REF'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+20:start+22]))
		cur['LF2REF'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+22:start+24]))
		cur['LF3REF'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+24:start+26]))
		cur['LF4REF'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+26:start+28]))

		cur['LED1SNS'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+28:start+30]))
		cur['LED2SNS'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+30:start+32]))
		cur['LED3SNS'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+32:start+34]))
		cur['LED4SNS'] = left_shift_8(hex_string_byte_to_signed_int(ps[start+34:start+36]))

		gyroscope = {}
		gyroscope['x'] = left_shift_8(int(ps[start+36:start+38], 16))
		gyroscope['y'] = left_shift_8(int(ps[start+38:start+40], 16))
		gyroscope['z'] = left_shift_8(int(ps[start+40:start+42], 16))
		cur['gyroscope'] = gyroscope

def parse_errors(ps, num_errors):
	errors = []
	start = 194
	for i in range(0, num_errors):
		cur = {}
		cur['error_code'] = int(ps[start:start+2],16) & 0x7F
		cur['priority_bit'] = int(ps[start:start+2],16) & 0x80
		cur['error_location'] = int(ps[start+2:start+4],16)
		cur['timestamp'] = int(ps[start+4:start+6],16)
		errors.append(cur)
		start += 6
	return errors
		

def parse_packet(ps):
	if (len(ps) != 510):
		print("Wrong size packet")
		return
	packet = {}
	packet['preamble'] = parse_preamble(ps)
	packet['current_info'] = parse_current_info(ps)
	message_type = packet['preamble']['message_type']
	if (message_type == '000'):
		packet['data'] = parse_idle_data(ps)
	elif (message_type == '001'):
		packet['data'] = parse_attitude_data(ps)
	elif (message_type == '010'):
		packet['data'] = parse_flash_burst_data(ps)
	elif (message_type == '011'):
		packet['data'] = parse_flash_comparison_data(ps)
	elif (message_type == '100'):
		packet['data'] = parse_low_power_data(ps)
	num_errors = packet['preamble']['num_errors']	
	packet['errors'] = parse_errors(ps, num_errors)
	packet_JSON = json.dumps(packet, indent=4)
	print(packet_JSON)



def main():
	test_packet = "574c39585a45030000002c960e0c010206030303030606f0f1020101010000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000009b2f00a034009c32009c31009b30009b2f00a034009c32009c31009b30009b2f00a034009c32009c310000003e9b3f7b56927f60a09390ba56dccf73954489ae1d77b4c1400450c5b2bab4e7"
	parse_packet(test_packet)	

if __name__ == "__main__":
    main()