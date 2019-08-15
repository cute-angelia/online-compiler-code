from __future__ import absolute_import, print_function

# Python3-friendly imports
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

import json
import logging

import tornado.web
import tornado.websocket
import base64
import uuid


def _cast_unicode(s):
    if isinstance(s, bytes):
        return s.decode("utf-8")
    return s


class TermSocket(tornado.websocket.WebSocketHandler):
    """Handler for a terminal websocket"""

    def initialize(self, term_manager):
        self.term_manager = term_manager
        self.term_name = ""
        self.size = (None, None)
        self.terminal = None

        self._logger = logging.getLogger(__name__)

    def origin_check(self, origin=None):
        """Deprecated: backward-compat for terminado <= 0.5."""
        ## return self.check_origin(origin or self.request.headers.get("Origin"))
        return True

    def check_origin(self, origin=None):
        return True

    def open(self, url_component=None):
        super(TermSocket, self).open(url_component)

        self._logger.info("TermSocket.open: %s", url_component)

        url_component = _cast_unicode(url_component)
        self.term_name = url_component or "tty"
        self.terminal = self.term_manager.get_terminal(url_component)
        for s in self.terminal.read_buffer:
            self.on_pty_read(s)
        self.terminal.clients.append(self)

        self.send_json_message(["setup", {}])
        self._logger.info("TermSocket.open: Opened %s", self.term_name)

    def on_pty_read(self, text):
        """Data read from pty; send to frontend"""
        self.send_json_message(["stdout", text])

    def send_json_message(self, content):
        json_msg = json.dumps(content)
        self.write_message(json_msg)

    def generate_code(self, language_id, code):
        # python
        subperfix = ""
        uid = str(uuid.uuid4())
        suid = "".join(uid.split("-"))

        filepath = "/tmp/" + suid
        execCmd = ""

        # cpp
        if (language_id >= 10 and language_id <= 15) or language_id == 98:
            subperfix = ".cpp"
            f = open(filepath + subperfix, "w")
            d = base64.b64decode(code.encode("utf-8"))

            oexecfile = filepath + subperfix

            print("write file", oexecfile, d.decode("utf-8"))
            f.write(d.decode("utf-8"))
            f.close()

            if language_id == 98:
                execCmd = "g++ -o " + filepath + " " + oexecfile + " && " + filepath
            if language_id == 10:
                execCmd = (
                    "/usr/local/gcc-7.2.0/bin/g++ -Wl,-rpath,/usr/local/gcc-7.2.0/lib64 -o "
                    + filepath
                    + " "
                    + oexecfile
                    + " && "
                    + filepath
                )
            if language_id == 11:
                execCmd = (
                    "/usr/local/gcc-6.4.0/bin/g++ -Wl,-rpath,/usr/local/gcc-6.4.0/lib64 -o "
                    + filepath
                    + " "
                    + oexecfile
                    + " && "
                    + filepath
                )
            if language_id == 12:
                execCmd = (
                    "/usr/local/gcc-6.3.0/bin/g++ -Wl,-rpath,/usr/local/gcc-6.3.0/lib64 -o "
                    + filepath
                    + " "
                    + oexecfile
                    + " && "
                    + filepath
                )
            if language_id == 13:
                execCmd = (
                    "/usr/local/gcc-5.4.0/bin/g++ -Wl,-rpath,/usr/local/gcc-5.4.0/lib64 -o "
                    + filepath
                    + " "
                    + oexecfile
                    + " && "
                    + filepath
                )
            if language_id == 14:
                execCmd = (
                    "/usr/local/gcc-4.9.4/bin/g++ -Wl,-rpath,/usr/local/gcc-4.9.4/lib64 "
                    + " "
                    + oexecfile
                    + " && "
                    + filepath
                )
            if language_id == 15:
                execCmd = (
                    "/usr/local/gcc-4.8.5/bin/g++ -Wl,-rpath,/usr/local/gcc-4.8.5/lib64 "
                    + " "
                    + oexecfile
                    + " && "
                    + filepath
                )

        # python
        if (language_id >= 34 and language_id <= 36) or language_id == 99:
            subperfix = ".py"
            f = open(filepath + subperfix, "w")
            d = base64.b64decode(code.encode("utf-8"))
            print("write file", filepath + subperfix, d.decode("utf-8"))
            f.write(d.decode("utf-8"))
            f.close()

            if language_id == 99:
                execCmd = "python " + filepath + subperfix
            if language_id == 34:
                execCmd = "/usr/local/python-3.6.0/bin/python3 " + filepath + subperfix
            if language_id == 35:
                execCmd = "/usr/local/python-3.5.3/bin/python3 " + filepath + subperfix
            if language_id == 36:
                execCmd = "/usr/local/python-2.7.9/bin/python " + filepath + subperfix
            if language_id == 37:
                execCmd = "/usr/local/python-2.6.9/bin/python " + filepath + subperfix
            # elif language_id == 35:
            # elif language_id == 36:
            # elif language_id == 37:

        return execCmd + "\n"

    def on_message(self, message):
        print(
            "TermSocket.on_message: %s - (%s) %s",
            self.term_name,
            type(message),
            len(message) if isinstance(message, bytes) else message[:250],
        )

        command = json.loads(message)
        msg_type = command[0]

        if msg_type == "stdin":
            self.terminal.ptyproc.write(command[1])
        elif msg_type == "input":
            self.terminal.ptyproc.write(command[1])
        elif msg_type == "code":
            ## self.terminal.ptyproc.write("\u0003")
            if len(command) < 4:
                return
            execCmd = self.generate_code(command[1], command[2])
            print("execCmd", execCmd)

            self.terminal.ptyproc.write(execCmd)
        elif msg_type == "set_size":
            self.size = command[1:3]
            self.terminal.resize_to_smallest()

    def on_close(self):
        self._logger.info("Websocket closed")
        if self.terminal:
            self.terminal.clients.remove(self)
            self.terminal.resize_to_smallest()
        self.term_manager.client_disconnected(self)

    def on_pty_died(self):
        """Terminal closed: tell the frontend, and close the socket.
        """
        self.send_json_message(["disconnect", 1])
        self.close()
        self.terminal = None
