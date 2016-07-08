import multiprocessing
import threading
import logging
import nnpy
import sys

from . import PFPSimDebugger_pb2 as pb

if sys.version_info[0] > 2:
    import queue
else:
    import Queue as queue

# TODO(gordon) this is temporary to be replaced by the protobuf object
from collections import namedtuple
Data = namedtuple('Data', ['id_', 'payload'])


class TraceManager(object):
    def __init__(self, ipc_url="ipc:///tmp/pfpdb-trace", topic="PFPDB"):
        self.ipc_url = ipc_url
        self.topic   = topic

        self._trace_dispatcher = None
        self.log = logging.getLogger("TraceManager")
        self.log.addHandler(logging.StreamHandler())

    def add_trace(self, trace_id, **kwargs):
        if self._trace_dispatcher is None:
            self.log.debug("Creating and starting trace dispatcher")
            self._trace_dispatcher = TraceManager._TraceDispatcher(self.ipc_url, self.topic)
            self._trace_dispatcher.start()

        self.log.debug("Creating and adding Trace")
        self._trace_dispatcher.add_trace(TraceManager._Trace(
            kwargs["x_axis"] if "x_axis" in kwargs else "",
            kwargs["y_axis"] if "y_axis" in kwargs else "",
            kwargs["title"]  if "title"  in kwargs else "",
            trace_id))

    class _TraceDispatcher(threading.Thread):
        def __init__(self, ipc_url, topic):
            super(TraceManager._TraceDispatcher, self).__init__()
            self.daemon = True

            self.queue = queue.Queue()
            self.sock  = nnpy.Socket(nnpy.AF_SP, nnpy.SUB)
            self.sock.setsockopt(nnpy.SUB, nnpy.SUB_SUBSCRIBE, topic)
            self.sock.connect(ipc_url)
            self.topic = topic

            self.log = logging.getLogger("_TraceDispatcher")
            self.log.addHandler(logging.StreamHandler())

        def add_trace(self, trace):
            self.log.debug("Enqueuing and starting trace")
            self.queue.put_nowait(trace)
            trace.start()

        def _deserialize_messages(self, messages):
            def _deserialize_message(msg):
                offset = len(self.topic)
                id_ = (ord(msg[offset]) << 8) | ord(msg[offset + 1])

                # Parses the header of the message to get the id, the actual
                # payload part will be dealt with in the multiprocess
                return Data(id_=id_, payload=msg[offset + 2:])

            return map(_deserialize_message, messages)

        def run(self):
            trace_map = {}
            while True:
                msgs = []
                # Read at least one message blockingly.
                self.log.debug("TraceDispatcher waiting for published msg")
                msgs.append(self.sock.recv())

                # Then read as many more as we can non-blockingly
                try:
                    while True:
                        msgs.append(self.sock.recv(nnpy.DONTWAIT))
                        self.log.debug("Trace dispatcher received additional msg")
                except AssertionError:
                    if nnpy.nanomsg.nn_errno() != nnpy.EAGAIN:
                        error_msg = nnpy.ffi.string(
                            nnpy.nanomsg.nn_strerror(nnpy.nanomsg.nn_errno()))
                        raise RuntimeError("Error in nanomsg recv: " + error_msg)

                # Now after receiving this batch of messages, but before processing them,
                # We will process the queue of new traces. This ensures any traces have themselves
                # initialized *before* messages belonging to them are processed.

                while not self.queue.empty():
                    self.log.debug("Trace dispatcher got new trace")
                    trace = self.queue.get_nowait()

                    if trace.id_ not in trace_map:
                        self.log.debug("Trace dispatcher storing trace with id %d"
                                       % trace.id_)
                        trace_map[trace.id_] = trace
                    else:
                        self.log.warning("Received duplicate trace id %d"
                                         % trace.id_)

                msgs = self._deserialize_messages(msgs)

                for msg in msgs:
                    if msg.id_ in trace_map:
                        self.log.debug("trace dispatcher received message for trace %d"
                                      % msg.id_)
                        trace_map[msg.id_].add_data(msg)
                    else:
                        self.log.warning("Received data for non-existant trace %d"
                                         % msg.id_)


    class _Trace(multiprocessing.Process):
        def __init__(self, x_axis, y_axis, title, trace_id):
            super(TraceManager._Trace, self).__init__()
            self.daemon = True

            self.queue    = multiprocessing.Queue()
            self.x_axis   = x_axis
            self.y_axis   = y_axis
            self.title    = title
            self.id_      = trace_id

            # TODO how does this work across subprocess boundary?
            self.log = logging.getLogger("_Trace%d" % trace_id)
            self.log.addHandler(logging.StreamHandler())

        def add_data(self, data):
            self.log.debug("Trace %d enqueuing data" % self.id_)
            self.queue.put_nowait(data)

        def run(self):
            self.log.debug("_Trace subprocess beginning")
            # matplotlib must be imported in each multiprocessing process
            # Furthermore, the only way to have multiple plots simultaneously
            # is to create them in seperate Process's (since they're truly
            # seperate OS level processes)
            import matplotlib.pyplot as plt
            # Create the figure for this process
            plt.figure()
            # Non blocking mode.
            plt.ion()

            plt.xlabel(self.x_axis)
            plt.ylabel(self.y_axis)
            plt.title(self.title)

            plt.pause(0.25) # Run plot window event loop to initialize the window
            self.log.debug("_Trace done creating figure")
            while True:
                i = 0
                while not self.queue.empty():
                    # TODO - restore protobuf message format after done testing.
                    self.log.debug("Trace %d dequeuing and scattering (%d)" % (self.id_, i))
                    i += 1

                    data = self.queue.get_nowait()

                    msg = pb.TracingUpdateMsg()
                    msg.ParseFromString(data.payload)

                    assert msg.id == data.id_

                    if msg.HasField("float_value"):
                        plt.scatter(msg.timestamp, msg.float_value)
                    elif msg.HasField("int_value"):
                        plt.scatter(msg.timestamp, msg.int_value)
                    else:
                        self.log.warning("Something wrong, no float or int value")

                plt.pause(0.001) # Run plot window event loop and updates

