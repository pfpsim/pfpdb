from pfpdb.pfpdb import DebuggerIPCSession
from pfpdb.pfpdb import PFPSimDebugger
from pfpdb.pfpdb import PFPSimDebuggerCmd
import pfpdb.pfpdb as pfpdb

from threading import Thread

import nnpy
from pfpdb import PFPSimDebugger_pb2 as pb2

from functools import partial

def dummy_model_main(url, rsp):
    """
    Dummy function to be used in a thread mocking a debugged
    model. Receives a single command and then sends the
    specified response.
    """
    sock = nnpy.Socket(nnpy.AF_SP, nnpy.REP)
    sock.bind(url)
    # Set one second receive timeout
    sock.setsockopt(nnpy.SOL_SOCKET, nnpy.RCVTIMEO, 1000)
    try:
        sock.recv()
        # Sock raises an assertion when it times out
    except AssertionError:
        return
    sock.send(rsp.SerializeToString())
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
import sys
if sys.version_info[0] < 3:
    from StringIO import StringIO
else:
    from io import StringIO


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

    test_method = partial(check_run, response, "run", "")
    test_method.description = "run with generic ack response"
    yield test_method
    test_method = partial(check_run, response, "r", "")
    test_method.description = "r with generic ack response"
    yield test_method

    #################################################################

    response      = pb2.DebugMsg()
    response.type = pb2.DebugMsg.PacketDropped

    submsg = pb2.PacketDroppedMsg()
    submsg.packet_id = 100
    submsg.module = "No Module"
    submsg.reason = "Just Because"

    response.message = submsg.SerializeToString()

    expected = ('\x1b[0mPacket Dropped!\n'+
               ('Packet ID: %d\n' % submsg.packet_id) +
               ('Module: %s\n'    % submsg.module) +
               ('Reason: %s'      % submsg.reason))

    test_method = partial(check_run, response, "run", expected)
    test_method.description = "run with packet_dropped response"
    yield test_method
    test_method = partial(check_run, response, "r", expected)
    test_method.description = "r with packet_dropped response"
    yield test_method

    #################################################################

    response      = pb2.DebugMsg()
    response.type = pb2.DebugMsg.ParsedPacketValue

    submsg = pb2.ParsedPacketValueMsg()

    h = submsg.headers.add()
    h.name = "Ethernet"
    f = h.fields.add()
    f.name  = "dst"
    f.value = b"\xAA\xBB\xCC\xAA\xBB\xCC"
    f = h.fields.add()
    f.name  = "src"
    f.value = b"\xFF\x01\x01\x01\x01\x01"

    h = submsg.headers.add()
    h.name = "IPv4"
    f = h.fields.add()
    f.name  = "dst"
    f.value = b"\x80\x00\x00\x01"
    f = h.fields.add()
    f.name  = "src"
    f.value = b"\x0A\x00\x00\x01"

    response.message = submsg.SerializeToString()

    expected = ("Ethernet:\n" +
                "  dst: AA:BB:CC:AA:BB:CC\n" +
                "  src: FF:01:01:01:01:01\n" +
                "\n" +
                "IPv4:\n" +
                "  dst: 80:00:00:01\n" +
                "  src: 0A:00:00:01\n")

    test_method = partial(check_run, response, "print 1", expected)
    test_method.description = "print parsed content of packet"
    yield test_method

def assert_text_equal(expected, actual):
    try:
        assert expected == actual
    except AssertionError:
        print "Expected:",expected
        print "Actual:",actual
        raise


def check_run(response_msg, run_command, expected_stdout):
    ipc_url = "ipc:///tmp/pfpdb-test.ipc"

    model_thread = Thread(target=dummy_model_main,
                          args=(ipc_url, response_msg))

    model_thread.start()

    ipc_session  = DebuggerIPCSession(ipc_url)
    debugger     = PFPSimDebugger(ipc_session, DummyProcess(), None, False)
    debugger_cli = PFPSimDebuggerCmd(debugger)

    with captured_output() as (out, err):
        debugger_cli.onecmd(run_command)

    assert_text_equal(expected_stdout, out.getvalue().strip())
    assert_text_equal("", err.getvalue().strip())

    model_thread.join()

