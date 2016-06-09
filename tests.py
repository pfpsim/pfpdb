from pfpdb.pfpdb import DebuggerIPCSession
from pfpdb.pfpdb import PFPSimDebugger
from pfpdb.pfpdb import PFPSimDebuggerCmd
import pfpdb.pfpdb as pfpdb

from threading import Thread

import nnpy
from pfpdb import PFPSimDebugger_pb2 as pb2

from functools import partial

from hexdump import hexdump

import sys

if sys.version_info[0] < 3:
    def str_to_bytes(s):
        return [c for c in s]
else:
    def str_to_bytes(s):
        return bytes(s)


def dummy_model_main(url, rsp):
    """
    Dummy function to be used in a thread mocking a debugged
    model. Receives a single command and then sends the
    specified response.
    """
    sock = nnpy.Socket(nnpy.AF_SP, nnpy.REP)
    sock.bind(url)
    sock.recv()
    sock.send(str_to_bytes(rsp.SerializeToString()))
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
                "  src: 0A:00:00:01")

    test_method = partial(check_run, response, "print 1", expected)
    test_method.description = "print parsed content of packet"
    yield test_method

    #################################################################
    response      = pb2.DebugMsg()
    response.type = pb2.DebugMsg.RawPacketValue

    submsg = pb2.RawPacketValueMsg()

    if sys.version_info[0] < 3:
        raw_data = ''.join(chr(c) for c in range(256))
    else:
        raw_data = bytes(range(256))

    submsg.value = raw_data

    response.message = submsg.SerializeToString()

    expected = (
            '00000000: 00 01 02 03 04 05 06 07  08 09 0A 0B 0C 0D 0E 0F  ................' + '\n' +
            '00000010: 10 11 12 13 14 15 16 17  18 19 1A 1B 1C 1D 1E 1F  ................' + '\n' +
            '00000020: 20 21 22 23 24 25 26 27  28 29 2A 2B 2C 2D 2E 2F   !"#$%&\'()*+,-./' + '\n' +
            '00000030: 30 31 32 33 34 35 36 37  38 39 3A 3B 3C 3D 3E 3F  0123456789:;<=>?' + '\n' +
            '00000040: 40 41 42 43 44 45 46 47  48 49 4A 4B 4C 4D 4E 4F  @ABCDEFGHIJKLMNO' + '\n' +
            '00000050: 50 51 52 53 54 55 56 57  58 59 5A 5B 5C 5D 5E 5F  PQRSTUVWXYZ[\]^_' + '\n' +
            '00000060: 60 61 62 63 64 65 66 67  68 69 6A 6B 6C 6D 6E 6F  `abcdefghijklmno' + '\n' +
            '00000070: 70 71 72 73 74 75 76 77  78 79 7A 7B 7C 7D 7E 7F  pqrstuvwxyz{|}~.' + '\n' +
            '00000080: 80 81 82 83 84 85 86 87  88 89 8A 8B 8C 8D 8E 8F  ................' + '\n' +
            '00000090: 90 91 92 93 94 95 96 97  98 99 9A 9B 9C 9D 9E 9F  ................' + '\n' +
            '000000A0: A0 A1 A2 A3 A4 A5 A6 A7  A8 A9 AA AB AC AD AE AF  ................' + '\n' +
            '000000B0: B0 B1 B2 B3 B4 B5 B6 B7  B8 B9 BA BB BC BD BE BF  ................' + '\n' +
            '000000C0: C0 C1 C2 C3 C4 C5 C6 C7  C8 C9 CA CB CC CD CE CF  ................' + '\n' +
            '000000D0: D0 D1 D2 D3 D4 D5 D6 D7  D8 D9 DA DB DC DD DE DF  ................' + '\n' +
            '000000E0: E0 E1 E2 E3 E4 E5 E6 E7  E8 E9 EA EB EC ED EE EF  ................' + '\n' +
            '000000F0: F0 F1 F2 F3 F4 F5 F6 F7  F8 F9 FA FB FC FD FE FF  ................'
            )

    test_method = partial(check_run, response, "print raw 1", expected)
    test_method.description = "print raw packet content"
    yield test_method

    #################################################################
    response      = pb2.DebugMsg()
    response.type = pb2.DebugMsg.GenericAcknowledge

    submsg = pb2.GenericAcknowledgeMsg()

    response.message = submsg.SerializeToString()

    test_method = partial(check_run, response, "print 1", "Cannot print packet 1")
    yield test_method
    test_method = partial(check_run, response, "print raw 1", "Cannot print packet 1")
    yield test_method
    test_method = partial(check_run, response, "print field ipv4.src 1 ipv", "Cannot print packet 1")
    yield test_method

    #################################################################
    response      = pb2.DebugMsg()
    response.type = pb2.DebugMsg.PacketFieldValue

    submsg = pb2.PacketFieldValueMsg()

    ip_addr = (192,255,0,1)

    if sys.version_info[0] < 3:
        submsg.value = ''.join(map(chr, ip_addr))
    else:
        submsg.value = bytes(ip_addr)

    response.message = submsg.SerializeToString()

    test_method = partial(check_run, response, "print field ipv4.src 1 ip4", "192.255.0.1")
    yield test_method
    test_method = partial(check_run, response, "print field ipv4.src 1 dec", "3237937153")
    yield test_method
    test_method = partial(check_run, response, "print field ipv4.src 1 hex", "C0:FF:00:01")
    yield test_method
    test_method = partial(check_run, response, "print field ipv4.src 1", "C0:FF:00:01")
    yield test_method


def assert_text_equal(expected, actual):
    try:
        assert expected == actual
    except AssertionError:
        print("Expected: "+repr(expected))
        print("Actual:   "+repr(actual))
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

