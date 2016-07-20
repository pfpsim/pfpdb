import multiprocessing
import threading
import logging
import nnpy
import sys
import warnings
import colour

from . import PFPSimDebugger_pb2 as pb

if sys.version_info[0] > 2:
    import queue
else:
    import Queue as queue

# TODO(gordon) this is temporary to be replaced by the protobuf object
from collections import namedtuple, OrderedDict
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

        self._trace_dispatcher.append_to_trace(parent_trace_id, trace_id,
                kwargs.get("title", ""), kwargs.get("y_axis",""))

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

                    trace.add_trace(trace.id_, trace.title, trace.y_axis)
                else:
                    self.log.warning("Received duplicate trace id %d"
                                     % trace.id_)

        def append_to_trace(self, parent_trace_id, trace_id, title, y_axis):
            """Associate an existing trace object with a new id"""
            with self.lock:
                if parent_trace_id not in self.trace_map:
                    self.log.warning("Tried to associate to non-existant trace %d" % parent_trace_id)
                elif trace_id in self.trace_map:
                    self.log.warning("Received duplicate trace id %d" % trace_id)
                else:
                    self.trace_map[trace_id] = self.trace_map[parent_trace_id]
                    self.trace_map[trace_id].add_trace(trace_id, title, y_axis)


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


    class _AxisColours(object):
        class _Axis(object):
            def __init__(self):
                self.max_hi = 1.0
                self.max_lo = 0.0
                self.hi     = 1.0
                self.lo     = 0.0
                self.traces = []

            def set_hue_range(self, lo, hi):
                self.max_hi = hi
                self.max_lo = lo
                self._recalculate_bounds()

            # TODO(gordon) each trace added currently will call this twice
            # I believe...
            def _recalculate_bounds(self):
                # Use at most 15% of the color range per trace. Subtract one
                # because if we only have one trace we want to have zero width,
                # And if we have zero traces it really doesn't matter.
                width_limit = (len(self) - 1)*0.15
                max_width   = self.max_hi - self.max_lo
                center      = self.max_lo + (self.max_hi - self.max_lo)/2.0

                width = min(width_limit, max_width)

                self.hi = center + (width/2.0)
                self.lo = center - (width/2.0)

            def add_trace(self, id_):
                self.traces.append(id_)
                self._recalculate_bounds()

            def get_color(self, n=None):
                if n is None:
                    return self.lo + (self.hi - self.lo)/2.0
                else:
                    return self.lo + n*(self.hi - self.lo)/len(self.traces)

            def __len__(self):
                return len(self.traces)

        def __init__(self):
            self.axes = OrderedDict()

        def add_trace(self, axis_label, trace_id):
            if axis_label not in self.axes:
                self.axes[axis_label] = TraceManager._AxisColours._Axis()

            self.axes[axis_label].add_trace(trace_id)

            # After adding a trace, we will recalculate the colors of all
            # TODO(gordon) probably we can be smarter about this.
            total_size = float(sum(len(ax) for ax in self.axes.values()))

            hue = 0.0
            # We allocate 20% of the range of colors to be buffer space
            # between axes. Half of that buffer goes at the beginning of
            # each range and half goes at the end
            gap = (0.2 / len(self.axes)) / 2

            for ax_name, ax in self.axes.items():
                size = float(len(ax)/total_size)
                lo   = hue + gap
                hi   = hue + size - gap
                ax.set_hue_range(lo, hi)
                hue += size

        # Returns ((r,g,b), trace_id) pairs
        def trace_colours(self):
            for ax in self.axes.values():
                size = float(len(ax))

                for i, trace in enumerate(ax.traces):
                    yield (colour.hsl2rgb((ax.get_color(i), 1.0, 0.35)), trace)

        # Returns ((r,g,b), axis_name) pairs
        def axis_colours(self):
            for ax_name, ax in self.axes.items():
                yield (colour.hsl2rgb((ax.get_color(), 1.0, 0.35)), ax_name)


    class _Trace(multiprocessing.Process):
        def __init__(self, x_axis, y_axis, title, trace_id):
            super(TraceManager._Trace, self).__init__()
            self.daemon = True

            self.data_queue  = multiprocessing.Queue()
            self.trace_queue = multiprocessing.Queue()
            self.x_axis      = x_axis
            self.y_axis      = y_axis
            self.title       = title
            self.id_         = trace_id

            # TODO how does this work across subprocess boundary?
            self.log = logging.getLogger("_Trace%d" % trace_id)
            self.log.addHandler(logging.StreamHandler())

            self.start()

        def add_trace(self, trace_id, title, y_axis):
            self.log.debug("Trace %d being added")
            self.trace_queue.put_nowait((trace_id, title, y_axis))

        def add_data(self, data):
            self.log.debug("Trace %d enqueuing data" % self.id_)
            self.data_queue.put_nowait(data)

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

                fig, root_ax = plt.subplots()

                line   = {}
                legend = []
                x      = {}
                y      = {}
                ax     = {}

                offset        = 1
                offset_inc    = 0.2

                fig_right     =  0.8
                fig_right_inc = -0.05

                ax_colours = TraceManager._AxisColours()

                # Non blocking mode.
                plt.show(block=False)
                fig.canvas.draw()

                plt.title("Trace %d" % self.id_)

                self.log.debug("_Trace done creating figure")
                while True:
                    # Queue of newly added traces.
                    while not self.trace_queue.empty():
                        id_, title, y_axis = self.trace_queue.get_nowait()

                        # Each trace has an x and y series associated to it
                        x[id_] = []
                        y[id_] = []

                        # Each unique y axis label has its own seperate axis
                        # TODO(gordon) this seems a little brittle, we are
                        # just magically relying on the axis labels here. We
                        # should introduce some kind of enum-like setup for
                        # this.
                        if len(ax) == 0:
                            # The first one uses the root axis
                            ax[y_axis] = root_ax

                            ax[y_axis].set_ylabel(y_axis)
                        elif y_axis not in ax:
                            # Subsequent ones create their own new axis
                            # if one does not already exist.
                            ax[y_axis] = root_ax.twinx()

                            # We set the ylabel of the extra axes
                            ax[y_axis].set_ylabel(y_axis)

                            ax[y_axis].spines["right"].set_position(("axes", offset))
                            offset += offset_inc

                            fig.subplots_adjust(right=fig_right)
                            fig_right += fig_right_inc

                        # Each trace has its own line
                        line[id_], = ax[y_axis].plot([], [])

                        ax_colours.add_trace(y_axis, id_)
                        for trace_colour, trace_id in ax_colours.trace_colours():
                            line[trace_id].set_color(trace_colour)

                        for axis_colour, axis_name in ax_colours.axis_colours():
                            ax[axis_name].yaxis.label.set_color(axis_colour)

                        # Update the legend entries with the newly added line
                        legend.append((line[id_], title))

                        # Refresh the figure's legend.
                        root_ax.legend((e[0] for e in legend),
                                       (e[1] for e in legend))


                    # For each incoming data point, we add it to the
                    # corresponding series
                    while not self.data_queue.empty():
                        # We dequeue and parse the protobuf message containing
                        # the data point
                        data = self.data_queue.get_nowait()
                        msg = pb.TracingUpdateMsg()
                        msg.ParseFromString(data.payload)

                        # Ensure that the message is valid
                        # TODO(gordon) handle this better.
                        assert msg.id == data.id_
                        assert msg.HasField("timestamp")
                        assert msg.HasField("float_value") or msg.HasField("int_value")

                        x[data.id_].append(msg.timestamp)

                        if msg.HasField("float_value"):
                            y[data.id_].append(msg.float_value)
                        else: # msg.HasField("int_value")
                            y[data.id_].append(msg.int_value)

                    # After updating all series, we update all the matplotlib
                    # line objects.
                    # TODO(gordon) we could be smarter about this and only
                    # update those that actually had new data added.
                    for i in line:
                        line[i].set_ydata(y[i])
                        line[i].set_xdata(x[i])

                    # Recalculate the limits of the plot
                    # TODO(gordon) we could be smarter about this (see above)
                    for axis in ax.values():
                        axis.relim()
                        axis.autoscale_view()

                    # Redraw and handle events
                    # TODO(gordon) is this not going to use crazy cpu?
                    # since we're just spinning around in the same loop?
                    fig.canvas.draw()
                    fig.canvas.flush_events()

