import multiprocessing
import threading
import logging
import nnpy
import sys
import warnings

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

    def _ensure_trace_dispatcher(self):
        if self._trace_dispatcher is None:
            self.log.debug("Creating and starting trace dispatcher")
            self._trace_dispatcher = TraceManager._TraceDispatcher(self.ipc_url, self.topic)
            self._trace_dispatcher.start()

    def add_trace(self, trace_id, **kwargs):
        self._ensure_trace_dispatcher()

        self.log.debug("Creating and adding Trace")
        self._trace_dispatcher.add_trace(TraceManager._Trace(
                kwargs.get("x_axis", ""), kwargs.get("y_axis", ""),
                kwargs.get("title", ""),  trace_id))

    def append_to_trace(self, parent_trace_id, trace_id, **kwargs):
        self._ensure_trace_dispatcher()

        self.log.debug("Adding new subscription to existing trace")

        self._trace_dispatcher.append_to_trace(parent_trace_id, trace_id)

    class _TraceDispatcher(threading.Thread):
        def __init__(self, ipc_url, topic):
            super(TraceManager._TraceDispatcher, self).__init__()
            self.daemon = True

            self.sock  = nnpy.Socket(nnpy.AF_SP, nnpy.SUB)
            self.sock.setsockopt(nnpy.SUB, nnpy.SUB_SUBSCRIBE, topic)
            self.sock.connect(ipc_url)
            self.topic = topic

            self.lock = threading.Lock()
            self.trace_map = {}

            self.log = logging.getLogger("_TraceDispatcher")
            self.log.addHandler(logging.StreamHandler())

        def add_trace(self, trace):
            """Add the trace to the internal map of trace-ids -> traces"""
            with self.lock:
                if trace.id_ not in self.trace_map:
                    self.log.debug("Trace dispatcher storing trace with id %d"
                                   % trace.id_)
                    self.trace_map[trace.id_] = trace
                else:
                    self.log.warning("Received duplicate trace id %d"
                                     % trace.id_)

        def append_to_trace(self, parent_trace_id, trace_id):
            """Associate an existing trace object with a new id"""
            with self.lock:
                if parent_trace_id not in self.trace_map:
                    self.log.warning("Tried to associate to non-existant trace %d" % parent_trace_id)
                elif trace_id in self.trace_map:
                    self.log.warning("Received duplicate trace id %d" % trace_id)
                else:
                    self.trace_map[trace_id] = self.trace_map[parent_trace_id]


        def _deserialize_messages(self, messages):
            def _deserialize_message(msg):
                offset = len(self.topic)
                id_ = (ord(msg[offset]) << 8) | ord(msg[offset + 1])

                # Parses the header of the message to get the id, the actual
                # payload part will be dealt with in the multiprocess
                return Data(id_=id_, payload=msg[offset + 2:])

            return map(_deserialize_message, messages)

        def run(self):
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


                msgs = self._deserialize_messages(msgs)

                with self.lock:
                    for msg in msgs:
                        if msg.id_ in self.trace_map:
                            self.log.debug("trace dispatcher received message for trace %d"
                                          % msg.id_)
                            self.trace_map[msg.id_].add_data(msg)
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

            self.start()

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
            import matplotlib.cbook

            # Ignore warning about using default backend
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=matplotlib.cbook.mplDeprecation)

                fig, ax = plt.subplots()

                line = {}
                x    = {}
                y    = {}

                # Non blocking mode.
                plt.show(block=False)
                fig.canvas.draw()

                plt.xlabel(self.x_axis)
                plt.ylabel(self.y_axis)
                plt.title(self.title)

                self.log.debug("_Trace done creating figure")
                while True:
                    while not self.queue.empty():
                        data = self.queue.get_nowait()

                        msg = pb.TracingUpdateMsg()
                        msg.ParseFromString(data.payload)

                        assert msg.id == data.id_

                        id_ = data.id_

                        if data.id_ not in line:
                            x[id_] = []
                            y[id_] = []
                            line[id_], = ax.plot(x[id_], y[id_])

                        x[id_].append(msg.timestamp)

                        if msg.HasField("float_value"):
                            y[id_].append(msg.float_value)
                        elif msg.HasField("int_value"):
                            y[id_].append(msg.int_value)
                        else:
                            self.log.warning("Something wrong, no float or int value")

                    for i in line:
                        line[i].set_ydata(y[i])
                        line[i].set_xdata(x[i])

                    ax.relim()
                    ax.autoscale_view()
                    fig.canvas.draw()
                    fig.canvas.flush_events()

