import socket

class HamLibConn:
    DEFAULT_ROTCTLD_PORT = 4533
    DEFAULT_ROTCTLD_IP = "localhost"
    DEFAULT_NET_TIMEOUT_S = 5

    def __init__(self, timeout=DEFAULT_NET_TIMEOUT_S):
        self.conn = None
        self.timeout = timeout

    def __del__(self):
        self.close()
    
    def close(self):
        """ Closes the connection to the rotator """
        if self.conn is not None:
            try:
                self.conn.close()
                self.conn = None
                return None
            except socket.error as e:
                return e
        return "connection already closed"

    def connect(self, ip=DEFAULT_ROTCTLD_IP, port=DEFAULT_ROTCTLD_PORT):
        """ Connects to a rotctld daemon on the given IP and port """
        self.close()
        try:
            self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn.settimeout(self.timeout)
            return self.conn.connect((ip, port))
        except socket.error as e:
            return e

    def get_pos(self):
        """ Returns the rotator's current azimuth and elevation """
        reply, err = self._send_cmd("p", numlines=2)  
        if err is not None:
            return 0, 0, err
        if len(reply) == 0:
            return 0, 0, "no reply"

        try:
            az = float(reply[0])
            el = float(reply[1])
            return az, el, None
        except TypeError as e:
            return 0, 0, e

    def set_pos(self, az, el):
        """ Sets the rotator's current azimuth and elevation setpoint to move to """
        return self._send_cmd("P %f %f" % (az, el))

    def reset(self):
        """ Triggers the rotator to reset and calibrate """
        return self._send_cmd("R")

    def _send_cmd(self, cmd, numlines=1):
        if self.conn == None:
            return [], "no connection"

        try:
            self.conn.send(cmd + "\n")
        except socket.error as e:
            return [], e

        reply, err = self._recv_lines(numlines)
        if err is not None:
            return [], err

        errpresent, errcode = HamLibConn._check_for_error(reply)
        if errcode is None:
            return reply, "error processing error"
        if errcode != 0:
            return reply, errcode
        return reply, None

    @staticmethod
    def _check_for_error(lines):
        if len(lines) > 0:
            line = lines[0]
            if len(line) >= 6 and line[0:4] == "RPRT":
                try:
                    errcode = int(line[4:])
                    return True, errcode
                except TypeError:
                    return True, None
        return False, 0

    def _recv_lines(self, num_lines):
        if num_lines <= 0:
            return [], None
        lines = []
        curline = ""
        while len(lines) < num_lines:
            try:
                byt = self.conn.recv(1)
            except socket.error as e:
                return lines, e

            if len(byt) == 0:
                return lines, "end of file"
            if byt == "\n":
                lines.append(curline)
                curline = ""
            else:
                curline = curline + byt

        return lines, None

if __name__ == "__main__":
    hconn = HamLibConn()
    # use this above with `python -i <this file>`