import subprocess

msg = "Nervously I loaded the twin ducks aboard the revolving platform."

p1 = subprocess.Popen(['./rsencode', msg, str(len(msg))], stdout=subprocess.PIPE)
encoded_msg, err = p1.communicate()

print("Encoded Msg: " + encoded_msg)
encoded_msg_list = list(encoded_msg)
encoded_msg_list[2] = "\x35"
encoded_msg_list[16] = "\x23"
encoded_msg_list[18] = "\x34"
encoded_msg_with_errors = "".join(encoded_msg_list)

print("Encoded Msg With Errors: " + encoded_msg_with_errors)
p2 = subprocess.Popen(['./rsdecode', encoded_msg_with_errors, str(len(encoded_msg_with_errors)), str(32)], stdout=subprocess.PIPE)
decoded_msg, err = p2.communicate()
print("Decoded Msg: " + decoded_msg)
