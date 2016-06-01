import unittest

from pfpdb import DebuggerIPCSession
from pfpdb import PFPSimDebugger
from pfpdb import PFPSimDebuggerCmd
import pfpdb

from threading import Thread

import nnpy
import PFPSimDebugger_pb2 as pb2

from functools import partial

def dummy_model_main(url, rsp):
    """
    Dummy function to be used in a thread mocking a debugged
    model. Receives a single command and then sends the
    specified response.
    """
    sock = nnpy.Socket(nnpy.AF_SP, nnpy.REP)
    sock.bind(url)
    sock.recv()
    sock.send(rsp)
    sock.close()

class DummyProcess(object):
    """
    Dummy class mocking the python subprocess object holding
    a running model.
    """
    def poll(self):
        return None

# http://stackoverflow.com/a/17981937/1084754
from contextlib import contextmanager
from StringIO import StringIO
import sys

@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err

def test_run():
    response      = pb2.DebugMsg()
    response.type = pb2.DebugMsg.GenericAcknowledge

    submsg = pb2.GenericAcknowledgeMsg()

    response.message = submsg.SerializeToString()

    response = response.SerializeToString()

    test_method = partial(check_run, response, "", "")
    test_method.description = "run with generic ack response"
    yield test_method

    #################################################################

    response      = pb2.DebugMsg()
    response.type = pb2.DebugMsg.PacketDropped

    submsg = pb2.PacketDroppedMsg()
    submsg.packet_id = 100
    submsg.module = "No Module"
    submsg.reason = "Just Because"

    response.message = submsg.SerializeToString()

    expected = (u'\x1b[0mPacket Dropped!\n'+
               (u'Packet ID: %d\n' % submsg.packet_id) +
               (u'Module: %s\n'    % submsg.module) +
               (u'Reason: %s'      % submsg.reason))
    response = response.SerializeToString()

    test_method = partial(check_run, response, "", expected)
    test_method.description = "run with packet_dropped response"
    yield test_method

    #################################################################


def check_run(response_msg, run_command, expected_stdout):
    ipc_url = "ipc:///tmp/pfpdb-test.ipc"

    model_thread = Thread(target=dummy_model_main,
                          args=(ipc_url, response_msg))

    model_thread.start()

    ipc_session  = DebuggerIPCSession(ipc_url)
    debugger     = PFPSimDebugger(ipc_session, DummyProcess(), None, False)
    debugger_cli = PFPSimDebuggerCmd(debugger)

    with captured_output() as (out, err):
        debugger_cli.do_run(run_command)

    assert out.getvalue().strip() == expected_stdout
    assert err.getvalue().strip() == ""

    model_thread.join()

