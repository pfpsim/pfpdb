#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# pfpdb: Debugger for models built with the PFPSim Framework
#
# Copyright (C) 2016 Concordia Univ., Montreal
#     Samar Abdi
#     Umair Aftab
#     Gordon Bailey
#     Faras Dewal
#     Shafigh Parsazad
#     Eric Tremblay
#
# Copyright (C) 2016 Ericsson
#     Bochra Boughzala
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.
#


# PFPSimDebugger
#
# Author: Eric Tremblay

__version__ = "1.0.0"
import os
import sys
import subprocess
import nnpy
import cmd
import argparse
import logging
import traceback
from functools import wraps
from tabulate import tabulate
from hexdump import hexdump
import json
from threading import Thread
from time import sleep
from . import PFPSimDebugger_pb2

# For tracing
import multiprocessing

if sys.version_info[0] > 2:
    from functools import reduce

# DebuggerIPCSession class - Handles the transmission and reception of messages to and from the DebuggerIPCServer
class DebuggerIPCSession:
    def __init__(self, url):
        self.url = url  # url on which the ipc will occur
        self.socket = nnpy.Socket(nnpy.AF_SP, nnpy.REQ) # create socket
        self.socket.setsockopt(nnpy.SOL_SOCKET, nnpy.RCVTIMEO, 100)
        self.socket.connect(self.url)   # connect socket

    # Send message through socket. The message must be an object generated from the protocol buffer compiler or a wrapper around such an object.
    def send(self, message):
        self.socket.send(message.SerializeToString())

    # Receive message from server through the socket.
    # TODO(gordon) There must be a more concise way of doing this
    def recv(self):
        data = self.socket.recv()
        recv_msg = PFPSimDebugger_pb2.DebugMsg()
        recv_msg.ParseFromString(data)
        if recv_msg.type == PFPSimDebugger_pb2.DebugMsg.CounterValue:
            child_msg = PFPSimDebugger_pb2.CounterValueMsg()
            child_msg.ParseFromString(recv_msg.message)
            return child_msg.value
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.AllCounterValues:
            child_msg = PFPSimDebugger_pb2.AllCounterValuesMsg()
            child_msg.ParseFromString(recv_msg.message)
            return child_msg.name_list, child_msg.value_list
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.AllBreakpointValues:
            child_msg = PFPSimDebugger_pb2.AllBreakpointValuesMsg()
            child_msg.ParseFromString(recv_msg.message)
            return child_msg
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.BreakpointHit:
            child_msg = PFPSimDebugger_pb2.BreakpointHitMsg()
            child_msg.ParseFromString(recv_msg.message)
            return recv_msg.type, child_msg
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.GenericAcknowledge:
            child_msg = PFPSimDebugger_pb2.GenericAcknowledgeMsg()
            child_msg.ParseFromString(recv_msg.message)
            return recv_msg.type, child_msg.status
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.WhoAmIReply:
            child_msg = PFPSimDebugger_pb2.WhoAmIReplyMsg()
            child_msg.ParseFromString(recv_msg.message)
            return child_msg
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.PacketListValues:
            child_msg = PFPSimDebugger_pb2.PacketListValuesMsg()
            child_msg.ParseFromString(recv_msg.message)
            return child_msg.id_list, child_msg.location_list, child_msg.time_list
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.WatchpointHit:
            child_msg = PFPSimDebugger_pb2.WatchpointHitMsg()
            child_msg.ParseFromString(recv_msg.message)
            return recv_msg.type, child_msg
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.AllWatchpointValues:
            child_msg = PFPSimDebugger_pb2.AllWatchpointValuesMsg()
            child_msg.ParseFromString(recv_msg.message)
            return child_msg
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.BacktraceReply:
            child_msg = PFPSimDebugger_pb2.BacktraceReplyMsg()
            child_msg.ParseFromString(recv_msg.message)
            return recv_msg.type, child_msg;
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.SimulationEnd:
            child_msg = PFPSimDebugger_pb2.SimulationEndMsg()
            child_msg.ParseFromString(recv_msg.message)
            return recv_msg.type, child_msg
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.SimulationStopped:
            child_msg = PFPSimDebugger_pb2.SimulationStoppedMsg()
            child_msg.ParseFromString(recv_msg.message)
            return recv_msg.type, child_msg
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.AllIgnoreModules:
            child_msg = PFPSimDebugger_pb2.AllIgnoreModulesMsg()
            child_msg.ParseFromString(recv_msg.message)
            return child_msg
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.SimulationTime:
            child_msg = PFPSimDebugger_pb2.SimulationTimeMsg()
            child_msg.ParseFromString(recv_msg.message)
            return child_msg.time_ns
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.PacketDropped:
            child_msg = PFPSimDebugger_pb2.PacketDroppedMsg()
            child_msg.ParseFromString(recv_msg.message)
            return recv_msg.type, child_msg
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.DroppedPackets:
            child_msg = PFPSimDebugger_pb2.DroppedPacketsMsg()
            child_msg.ParseFromString(recv_msg.message)
            return child_msg
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.TableEntries:
            child_msg = PFPSimDebugger_pb2.TableEntriesMsg()
            child_msg.ParseFromString(recv_msg.message)
            return child_msg;
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.ParsedPacketValue:
            child_msg = PFPSimDebugger_pb2.ParsedPacketValueMsg()
            child_msg.ParseFromString(recv_msg.message)
            return recv_msg.type, child_msg
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.RawPacketValue:
            child_msg = PFPSimDebugger_pb2.RawPacketValueMsg()
            child_msg.ParseFromString(recv_msg.message)
            return recv_msg.type, child_msg
        elif recv_msg.type == PFPSimDebugger_pb2.DebugMsg.PacketFieldValue:
            child_msg = PFPSimDebugger_pb2.PacketFieldValueMsg()
            child_msg.ParseFromString(recv_msg.message)
            return recv_msg.type, child_msg
        else:
            return recv_msg.type, recv_msg

# DebuggerMessage class - Base class for wrappers around protobuf objects
class DebuggerMessage(object):
    def __init__(self, type_):
        self.parent_msg = PFPSimDebugger_pb2.DebugMsg()
        self.message = None
        self.parent_msg.type = type_

    def SerializeToString(self):
        self.SerializeMessage()
        return self.parent_msg.SerializeToString()

    def SerializeMessage(self):
        if self.message != None:
            self.parent_msg.message = self.message.SerializeToString()

# Wrappers around protobuf objects. They must inherit DebuggerMessage and set their own type
class RunMessage(DebuggerMessage):
    def __init__(self, time_ns = None):
        super(RunMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.Run)
        self.message = PFPSimDebugger_pb2.RunMsg()
        if time_ns != None:
            self.message.time_ns = str(time_ns)
            print("Session - run time: " + self.message.time_ns)

class GetCounterMessage(DebuggerMessage):
    def __init__(self, name):
        super(GetCounterMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.GetCounter)
        self.message = PFPSimDebugger_pb2.GetCounterMsg()
        self.message.name = name

class GetAllCountersMessage(DebuggerMessage):
    def __init__(self):
        super(GetAllCountersMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.GetAllCounters)
        self.message = PFPSimDebugger_pb2.GetAllCountersMsg()

class SetBreakpointMessage(DebuggerMessage):
    def __init__(self, condition, value, temp, disabled):
        super(SetBreakpointMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.SetBreakpoint)
        self.message = PFPSimDebugger_pb2.SetBreakpointMsg()
        if temp is True:
            self.message.temporary = '1'
        else:
            self.message.temporary = '0'
        if disabled is True:
            self.message.disabled = '1'
        else:
            self.message.disabled = '0'

        for i,cond in enumerate(condition):
            self.message.condition_list.append(cond)
            self.message.value_list.append(value[i])

class ContinueMessage(DebuggerMessage):
    def __init__(self, time_ns = None):
        super(ContinueMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.Continue)
        self.message = PFPSimDebugger_pb2.ContinueMsg()
        if time_ns != None:
            self.message.time_ns = str(time_ns)

class GetAllBreakpointsMessage(DebuggerMessage):
    def __init__(self):
        super(GetAllBreakpointsMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.GetAllBreakpoints)
        self.message = PFPSimDebugger_pb2.GetAllBreakpointsMsg()

class RemoveBreakpointMessage(DebuggerMessage):
    def __init__(self, bkpt_id):
        super(RemoveBreakpointMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.RemoveBreakpoint)
        self.message = PFPSimDebugger_pb2.RemoveBreakpointMsg()
        self.message.id = str(bkpt_id);

class WhoAmIMessage(DebuggerMessage):
    def __init__(self):
        super(WhoAmIMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.WhoAmI)
        self.message = PFPSimDebugger_pb2.WhoAmIMsg()

class NextMessage(DebuggerMessage):
    def __init__(self):
        super(NextMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.Next)
        self.message = PFPSimDebugger_pb2.NextMsg()

class GetPacketListMessage(DebuggerMessage):
    def __init__(self, module = None):
        super(GetPacketListMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.GetPacketList)
        self.message = PFPSimDebugger_pb2.GetPacketListMsg()
        if module != None:
            self.message.module = module

class SetWatchpointMessage(DebuggerMessage):
    def __init__(self, counter, disabled):
        super(SetWatchpointMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.SetWatchpoint)
        self.message = PFPSimDebugger_pb2.SetWatchpointMsg()
        self.message.counter_name = counter
        if disabled is True:
            self.message.disabled = '1'
        else:
            self.message.disabled = '0'

class GetAllWatchpointValuesMessage(DebuggerMessage):
    def __init__(self):
        super(GetAllWatchpointValuesMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.GetAllWatchpoints)
        self.message = PFPSimDebugger_pb2.GetAllWatchpointsMsg()

class RemoveWatchpointMessage(DebuggerMessage):
    def __init__(self, wp_id):
        super(RemoveWatchpointMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.RemoveWatchpoint)
        self.message = PFPSimDebugger_pb2.RemoveWatchpointMsg()
        self.message.id = str(wp_id)

class BacktraceMessage(DebuggerMessage):
    def __init__(self, pk_id = None):
        super(BacktraceMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.Backtrace)
        self.message = PFPSimDebugger_pb2.BacktraceMsg()
        if pk_id != None:
            self.message.packet_id = str(pk_id)

class EnableDisableBreakpointMessage(DebuggerMessage):
    def __init__(self, bk_id, enable):
        super(EnableDisableBreakpointMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.EnableDisableBreakpoint)
        self.message = PFPSimDebugger_pb2.EnableDisableBreakpointMsg()
        self.message.id = str(bk_id)
        if enable is True:
            self.message.enable = '1'
        else:
            self.message.enable = '0'

class EnableDisableWatchpointMessage(DebuggerMessage):
    def __init__(self, wp_id, enable):
        super(EnableDisableWatchpointMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.EnableDisableWatchpoint)
        self.message = PFPSimDebugger_pb2.EnableDisableWatchpointMsg()
        self.message.id = str(wp_id)
        if enable is True:
            self.message.enable = '1'
        else:
            self.message.enable = '0'

class IgnoreModuleMessage(DebuggerMessage):
    def __init__(self, module, delete = False):
        super(IgnoreModuleMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.IgnoreModule)
        self.message = PFPSimDebugger_pb2.IgnoreModuleMsg()
        self.message.module = module
        self.message.delete = delete;

class GetAllIgnoreModulesMessage(DebuggerMessage):
    def __init__(self):
        super(GetAllIgnoreModulesMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.GetAllIgnoreModules)
        self.message = PFPSimDebugger_pb2.GetAllIgnoreModulesMsg()

class GetSimulationTimeMessage(DebuggerMessage):
    def __init__(self):
        super(GetSimulationTimeMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.GetSimulationTime)
        self.message = PFPSimDebugger_pb2.GetSimulationTimeMsg()

class BreakOnPacketDropMessage(DebuggerMessage):
    def __init__(self, on):
        super(BreakOnPacketDropMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.BreakOnPacketDrop)
        self.message = PFPSimDebugger_pb2.BreakOnPacketDropMsg()
        self.message.on = on

class GetDroppedPacketsMessage(DebuggerMessage):
    def __init__(self):
        super(GetDroppedPacketsMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.GetDroppedPackets)
        self.message = PFPSimDebugger_pb2.GetDroppedPacketsMsg()

# Control Plane Messages
class CPCommandMessage(DebuggerMessage):
    def __init__(self, command):
        super(CPCommandMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.CPCommand)
        self.message = PFPSimDebugger_pb2.CPCommandMsg()
        self.message.command = command

class GetTableEntriesMessage(DebuggerMessage):
    def __init__(self):
        super(GetTableEntriesMessage, self).__init__(PFPSimDebugger_pb2.DebugMsg.GetTableEntries)
        self.message = PFPSimDebugger_pb2.GetTableEntriesMsg()

class GetParsedPacketMessage(DebuggerMessage):
    def __init__(self, id):
        super(GetParsedPacketMessage, self).__init__(
                PFPSimDebugger_pb2.DebugMsg.GetParsedPacket)
        self.message = PFPSimDebugger_pb2.GetParsedPacketMsg()
        self.message.id = id

class GetRawPacketMessage(DebuggerMessage):
    def __init__(self, id):
        super(GetRawPacketMessage, self).__init__(
                PFPSimDebugger_pb2.DebugMsg.GetRawPacket)
        self.message = PFPSimDebugger_pb2.GetRawPacketMsg()
        self.message.id = id

class GetPacketFieldMessage(DebuggerMessage):
    def __init__(self, id, field_name):
        super(GetPacketFieldMessage, self).__init__(
                PFPSimDebugger_pb2.DebugMsg.GetPacketField)
        self.message = PFPSimDebugger_pb2.GetPacketFieldMsg()
        self.message.id = id
        self.message.field_name = field_name

class StartTracingMessage(DebuggerMessage):
    def __init__(self, **kwargs):
        super(StartTracingMessage, self).__init__(
                PFPSimDebugger_pb2.DebugMsg.StartTracing)
        self.message = PFPSimDebugger_pb2.StartTracingMsg()

        if "counter" in kwargs:
            self.message.type = PFPSimDebugger_pb2.StartTracingMsg.COUNTER
            self.message.name = kwargs["counter"]
        elif "throughput" in kwargs:
            raise NotImplemented("Tracing throughput not yet implemented")
        elif "from_latency" in kwargs and "to_latency" in kwargs:
            raise NotImplemented("Tracing latency not yet implemented")
        else:
            raise TypeError("Missing required Keyword Args, one of: 'counter',"
                          + " 'throughput', or ('from_latency','to_latency')")


# PFPSimDebugger class - Manages requests and replies through the IPC Session and the child process. Creates a layer of abstraction between the front end of the debugger and the ipc session and the child process.
class PFPSimDebugger(object):
    def __init__(self, ipc_session, process, pid, verbose):
        self.ipc_session = ipc_session
        self.process = process
        self.pid = pid
        self.log = logging.getLogger("cmd_logger")
        self.log.addHandler(logging.StreamHandler())
        self.traces = {}
        if verbose:
            self.log.setLevel("DEBUG")

    def recv(self):
        while(1):
            try:
                return self.ipc_session.recv()
            except AssertionError:
                if nnpy.nanomsg.nn_errno() not in (nnpy.ETIMEDOUT, nnpy.EAGAIN):
                    error_msg = nnpy.ffi.string(nnpy.nanomsg.nn_strerror(nnpy.nanomsg.nn_errno()))
                    raise RuntimeError("Error in nanomsg recv: " + error_msg)
                else:
                    # The read timed out. If the process is dead, we should terminate, otherwise do
                    # nothing and try again
                    if self.process is not None:
                        exit_code = self.process.poll()
                        if exit_code != None:
                            print("The child process has exited. Exit Code: " + str(exit_code))
                            sys.exit(1)
                    # Used when attaching to running simulation
                    else:
                        try:
                            os.kill(int(self.pid), 0)
                        except OSError:
                            print("The attached process is no longer running.")
                            sys.exit(0)

    def run(self, time_ns = None):
        self.log.debug("Request: Run")
        if time_ns != None:
            request = RunMessage(time_ns)
        else:
            request = RunMessage()
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, reply = self.recv()
        self.log.debug("Msg Recieved!")
        return msg_type, reply

    def restart(self):
        if self.process is None:
            return False
        else:
            if self.process.poll() == None:
                self.log.debug("Killing simulation...")
                self.process.kill()
            self.log.debug("Starting simulation...")
            self.process = start_simulation()
            return True

    def print_counter(self, counter_name):
        self.log.debug("Request: Get Counter Value for " + counter_name)
        request = GetCounterMessage(counter_name)
        return self.__sendrecv(request)

    def print_all_counters(self):
        self.log.debug("Request: Get All Counter Values")
        request = GetAllCountersMessage()
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        names, values = self.recv()
        self.log.debug("Msg Received!")
        return names, values

    def print_packets(self, module = None):
        self.log.debug("Request: Get Packet List")
        if module == None:
            request = GetPacketListMessage();
        else:
            request = GetPacketListMessage(module);
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        ids, locations, times = self.recv()
        self.log.debug("Msg Received!")
        return ids, locations, times

    def get_parsed_packet(self, packet_id):
        self.log.debug("Request: Get parsed packet")

        request = GetParsedPacketMessage(packet_id)
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, recv_msg = self.recv()
        self.log.debug("Msg Received!")
        return msg_type, recv_msg

    def get_raw_packet(self, packet_id):
        self.log.debug("Request: Get raw packet")

        request = GetRawPacketMessage(packet_id)
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, recv_msg = self.recv()
        self.log.debug("Msg Received!")
        return msg_type, recv_msg

    def get_packet_field(self, packet_id, field_name):
        self.log.debug("Request: Get packet field: " + field_name + " for packet " + str(packet_id))

        request = GetPacketFieldMessage(packet_id, field_name)
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, recv_msg = self.recv()
        self.log.debug("Msg Received!")
        return msg_type, recv_msg

    def start_trace_counter(self, counter_name):
        def multiprocess_trace_run():
            import nnpy
            # I'm not 100% sure if PUB-SUB is the right model for this.
            # For sure it will work, and it does make the code simpler on
            # The C++ side because it only has to manage one socket.
            s = nnpy.Socket(nnpy.AF_SP, nnpy.SUB)
            # This may seem like a complicated scheme for subscribe topic
            # names, but this makes the C++ side simpler, and should work
            # Well in general. Nanomessage topic subscriptions just match
            # The leading bytes, so if we just convert the ID to a string
            # we'd still need to pad it with zeros, because "PFPDB1"
            # would also match messages for "PFPDB10". This way we still
            # support 65536 traces at the same time, which should be
            # far more than enough.
            #topic = ("PFPDB" +
                     #chr(self.id & 0xFF) +
                     #chr((self.id >> 8) & 0xff))
            topic = "PFPDB"
            s.connect("ipc:///tmp/pfpdb-trace")
            s.setsockopt(nnpy.SUB, nnpy.SUB_SUBSCRIBE, topic)

            print("Subscribed to topic " + repr(topic))

            # Now set up the matlab plot.
            import matplotlib.pyplot as plt
            plt.figure()
            plt.ion() # non-blocking

            while True:
                msgs = []
                try:
                    while True:
                        msgs.append(s.recv(nnpy.DONTWAIT))
                except AssertionError:
                    if nnpy.nanomsg.nn_errno() != nnpy.EAGAIN:
                        error_msg = nnpy.ffi.string(
                            nnpy.nanomsg.nn_strerror(nnpy.nanomsg.nn_errno()))
                        raise RuntimeError("Error in nanomsg recv: " + error_msg)

                for msg_str in msgs:
                    print("received: " + msg_str)
                    msg_str = msg_str[len("PFPDBXX"):] # Chop off topic prefix

                    #msg = PFPSimDebugger_pb2.TracingUpdateMsg()
                    #msg.ParseFromString(msg_str)

                    x,y = map(float, msg_str.split(","))
                    plt.scatter(x, y)

                    #if msg.HasField("float_value"):
                        #plt.scatter(msg.timestamp, msg.float_value)
                    #elif msg.HasField("int_value"):
                        #plt.scatter(msg.timestamp, msg.int_value)
                    #else:
                        #print("Something wrong, no float or int value")

                plt.pause(0.0001) # Run plot window event loop and updates

        self.log.debug("Request: Start tracing counter " + counter_name)

        request = StartTracingMessage(counter=counter_name)
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, recv_msg = self.recv()
        self.log.debug("Msg Received!")

        print("start_trace_counter: recieved type: " + str(msg_type))

        if msg_type == PFPSimDebugger_pb2.DebugMsg.StartTracingStatus:
            msg = PFPSimDebugger_pb2.StartTracingStatusMsg()
            msg.ParseFromString(recv_msg.message)

            trace_id = msg.id
            trace_proc = multiprocessing.Process(target=multiprocess_trace_run)
            self.traces[trace_id] = trace_proc

            trace_proc.daemon = True
            trace_proc.start()
            return True
        else:
            return False


    def continue_(self, time_ns = None):
        self.log.debug("Request: Continue")
        if time_ns != None:
            request = ContinueMessage(time_ns)
        else:
            request = ContinueMessage()
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, reply = self.recv()
        self.log.debug("Msg Received!")
        return msg_type, reply

    def next(self):
        request = NextMessage()
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, reply = self.recv()
        self.log.debug("Msg Recieved!")
        return msg_type, reply

    def set_breakpoint(self, conditions, values, temp, disabled):
        request = SetBreakpointMessage(conditions, values, temp, disabled)
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, reply = self.recv()
        self.log.debug("Msg Recieved!")
        return msg_type, reply

    def delete_breakpoint(self, bkpt_id):
        request = RemoveBreakpointMessage(bkpt_id)
        return self.__sendrecv(request)

    def get_breakpoints(self):
        request = GetAllBreakpointsMessage()
        return self.__sendrecv(request)

    def disable_breakpoint(self, bkpt_id):
        request = EnableDisableBreakpointMessage(bkpt_id, False)
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, reply = self.recv()
        self.log.debug("Msg Received!")
        return msg_type, reply

    def enable_breakpoint(self, bkpt_id):
        request = EnableDisableBreakpointMessage(bkpt_id, True)
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, reply = self.recv()
        self.log.debug("Msg Received!")
        return msg_type, reply

    def set_watchpoint(self, counter_name, disabled):
        request = SetWatchpointMessage(counter_name, disabled)
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, reply = self.recv()
        self.log.debug("Msg Recieved!")
        return msg_type, reply

    def delete_watchpoint(self, wp_id):
        request = RemoveWatchpointMessage(wp_id)
        return self.__sendrecv(request)

    def get_watchpoints(self):
        request = GetAllWatchpointValuesMessage()
        return self.__sendrecv(request)

    def disable_watchpoint(self, wp_id):
        request = EnableDisableWatchpointMessage(wp_id, False)
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, reply = self.recv()
        self.log.debug("Msg Received!")
        return msg_type, reply

    def enable_watchpoint(self, wp_id):
        request = EnableDisableWatchpointMessage(wp_id, True)
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, reply = self.recv()
        self.log.debug("Msg Received!")
        return msg_type, reply

    def backtrace(self, packet_id = None):
        if packet_id != None:
            request = BacktraceMessage(packet_id)
        else:
            request = BacktraceMessage();
        self.log.debug("Request: Backtrace")
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, reply = self.recv()
        self.log.debug("Msg Received!")
        return msg_type, reply

    def whoami(self):
        request = WhoAmIMessage()
        return self.__sendrecv(request)

    def ignore_module(self, module):
        request = IgnoreModuleMessage(module)
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, reply = self.recv()
        self.log.debug("Msg Received!")
        return msg_type, reply

    def delete_ignore_module(self, module):
        request = IgnoreModuleMessage(module, True)
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        msg_type, reply = self.recv()
        self.log.debug("Msg Received!")
        return msg_type, reply

    def get_ignore_modules(self):
        request = GetAllIgnoreModulesMessage()
        return self.__sendrecv(request)

    def get_simulation_time(self):
        request = GetSimulationTimeMessage()
        return self.__sendrecv(request)

    def break_on_packet_drop(self):
        request = BreakOnPacketDropMessage(True)
        return self.__sendrecv(request)

    def delete_break_on_packet_drop(self):
        request = BreakOnPacketDropMessage(False)
        return self.__sendrecv(request)

    def get_dropped_packets(self):
        request = GetDroppedPacketsMessage()
        return self.__sendrecv(request)

    def quit(self):
        if self.process is not None:
            if self.process.poll() == None:
                self.process.kill()

    def cp_command(self, command):
        request = CPCommandMessage(command)
        return self.__sendrecv(request)

    def get_table_entries(self):
        request = GetTableEntriesMessage()
        msg  = self.__sendrecv(request)
        table_entries = {}
        for entry in msg.entry_list:
            table_entry = {'table_name' : entry.table_name, 'match_key' : entry.match_key_list, 'action_name' : entry.action_name, 'handle' : entry.handle, 'status' : entry.status, 'action_data' : entry.action_data_list}
            if entry.table_name in table_entries:
                if entry.action_name in table_entries[entry.table_name]:
                    table_entries[entry.table_name][entry.action_name].append(table_entry)
                else:
                    table_entries[entry.table_name][entry.action_name] = [table_entry]
            else:
                table_entries[entry.table_name] = {}
                table_entries[entry.table_name][entry.action_name] = [table_entry]

        return table_entries;

    def __sendrecv(self, request):
        self.ipc_session.send(request)
        self.log.debug("Msg Sent!")
        reply = self.recv()
        self.log.debug("Msg Received!")
        return reply


# BadInputException - Exception raised when the the command is incorrect in any way
class BadInputException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

def handle_bad_input(func):
    @wraps(func)
    def func_wrapper(self, line):
        try:
            return func(self, line)
        except BadInputException as e:
            print("Incorrect %s command. Use 'help' command to see correct syntax." % (e))
    return func_wrapper

# PFPSimDebuggerCmd class - Command Line Interface for PFPSimDebugger
class PFPSimDebuggerCmd(cmd.Cmd):
    def __init__(self, debugger):
        cmd.Cmd.__init__(self)	# Call cmd.Cmd constructor
        self.prompt = "\033[36m(PFPSimDebug) \033[0m"
        self.debugger = debugger
        self.run_called = False
        self.sim_ended = False

    # run command - starts running the simulation
    @handle_bad_input
    def do_run(self, line):
        '''
run <time> <units>
r <time> <units>
    Use this command to start the simulation from within the PFPSimDebugger. If a time and unit is given, the simulation
    will run for the indicated amount of simulation time if it is not interrupted by a breakpoint hit. If not given, the
    simulation will run until completion or a breakpoint hit.
    Supported units:
        ns (nanoseconds)
        us (microseconds)
        ms (milliseconds)
        s (seconds)
        m (minutes)
        h (hours)
        '''
        if self.run_called is False:
            args = line.split(" ")
            if args[0] != '':
                try:
                    time = args[0]
                    unit = args[1]
                    time_final = self.getTimeInNS(time, unit)
                    msg_type, reply = self.debugger.run(time_final)
                except:
                    raise BadInputException("run")
            else:
                msg_type, reply = self.debugger.run();
            self.run_called = True
            self.handleRunOrContinueReply(msg_type, reply)
        else:
            if self.sim_ended is True:
                print("Simulation has ended.")
            else:
                print("Simulation is already started.")
            response = ""
            while response != "y" and response != "n":
                response = raw_input("Do you wish to restart it? y or n? ")
            if response == "y":
                print("Restarting simulation...")
                self.do_restart(line)

    # r command - same as run
    def do_r(self, line):
        '''
run <time> <units>
r <time> <units>
    Use this command to start the simulation from within the PFPSimDebugger. If a time and unit is given, the simulation
    will run for the indicated amount of simulation time if it is not interrupted by a breakpoint or watchpoint. If not
    given, the simulation will run until completion or until a breakpoint or watchpoint.
    Supported units:
        ns (nanoseconds)
        us (microseconds)
        ms (milliseconds)
        s (seconds)
        m (minutes)
        h (hours)
        '''
        self.do_run(line)

    @handle_bad_input
    def do_restart(self, line):
        '''
restart
    Use this command to restart the simulation from the beginning without removing any breakpoints or watchpoints.

restart clean
    Use this command to restart the simulation from the beginning and remove the currently set breakpoints and
    watchpoints. It is equivalent to quitting the PFPSimDebugger and starting it again.
        '''

        args = line.split(" ")
        if args[0] == "clean":
            clean = True
        elif args[0] == '':
            clean = False
        else:
            raise BadInputException("restart")
        self.run_called = False
        self.sim_ended = False
        if not clean:
            # Save breakpoints and watchpoints
            bkpts = self.debugger.get_breakpoints()
            wps = self.debugger.get_watchpoints()
            ignore = self.debugger.get_ignore_modules()
        # Restart simulation
        result = self.debugger.restart()
        if result is True:
            if not clean:
                # Reinsert breakpoints and watchpoints
                for i in range(len(bkpts.id_list)):
                    self.debugger.set_breakpoint(bkpts.breakpoint_condition_list[i].condition_list, bkpts.breakpoint_condition_list[i].value_list, bkpts.temporary[i], bkpts.disabled[i])

                for j in range(len(wps.id_list)):
                    self.debugger.set_watchpoint(wps.name_list[j], wps.disabled[j])

                for k in range(len(ignore.module_list)):
                    self.debugger.ignore_module(ignore.module_list[k])
        else:
            print("Cannot restart an attached process")

    @handle_bad_input
    def do_trace(self, line):
        '''
trace counter <counter_name>
trace -c <counter_name>
    Start tracing a given counter. This sets up a subscription to receive
    updates from the model being debugged whenever this counter's value changes
    and to plot the value of the counter over time.
        '''
        args = line.split()
        if len(args) == 2 and args[0] in ('counter','-c'):
            status = self.debugger.start_trace_counter(args[1])
            if status:
                print("Trace started")
            else:
                print("Failed to start trace for counter " + args[1])
        else:
            raise BadInputException("trace")

    # print command - obtain information from simulation and print it to screen
    @handle_bad_input
    def do_print(self, line):
        '''
print counter <counter_name>
print -c <counter_name>
    Print the value of the given counter. Use the name 'all' to print a list of all the counters within the simulation
    and their corresponding values. Auto-completion of the counter name is supported.

print packets <filters>
print -p <filters>
    Print the list of packets that are currently in the simulation.  The filters are optional.

    filters:
        -m <module_name>
            Will only print packets which are currently in the given module.

print raw <packet id>
    Print the raw contents of the given packet in a hexdump format.

    Once a packet is parsed, this prints only the unparsed payload, before
    a packet is parsed or after it is deparsed, this prints the entire raw
    content of the packet

print <packet id>
    Print the parsed contents of the given packet.

    Before the packet is parsed, the output of this command is undefined.

print field <field name> <packet id> [<output format>]
    Print the value of the specified field in the given packet.

    Output format is one of:
      hex (default): prints a hexadecimal representation of the field data
      dec          : prints a decimal representation of the field data
      ip4          : prints the field as an IPv4 address. Only valid for 4-byte fields


print dropped_packets
    Print the list of packets that have been dropped.
        '''


        args = line.split(" ")
        if args[0] == "counter" or args[0] == "-c":
            try:
                counter_name = args[1]
            except:
                raise BadInputException("print")
            if counter_name == 'all':
                names, values = self.debugger.print_all_counters()
                table = []
                for i,name in enumerate(names):
                    table.append([name, values[i]])
                print(tabulate(table, headers=["Counter Name", "Value"]))
            else:
                reply = self.debugger.print_counter(counter_name)
                if reply == -1:
                    print("No counter with name " + counter_name + " was found.")
                else:
                    print(counter_name + ": " + str(reply))
        elif args[0] == "packets" or args[0] == "-p":
            if len(args) == 3:
                if args[1] == "-m":
                    module = args[2]
                    ids, locations, times = self.debugger.print_packets(module)
                else:
                    raise BadInputException("print")
            elif len(args) == 1:
                ids, locations, times = self.debugger.print_packets()
            else:
                raise BadInputException("print")
            table = []
            for i, ident in enumerate(ids):
                table.append([ident, locations[i], times[i]])

            print(tabulate(table, headers=["Packet ID", "Module", "Time (ns)"], numalign="left"))
        elif args[0] == "dropped_packets":
            if len(args) > 1:
                raise BadInputException("print")
            else:
                reply = self.debugger.get_dropped_packets()
                table = []
                for i, mod in enumerate(reply.module_list):
                    table.append([reply.packet_id_list[i], mod, reply.reason_list[i]])
                print(tabulate(table, headers=["Packet ID", "Module", "Reason"], numalign="left"))
        elif args[0].isdigit() and len(args) == 1:
            msg_type, packet_data = self.debugger.get_parsed_packet(int(args[0]))

            if msg_type == PFPSimDebugger_pb2.DebugMsg.GenericAcknowledge:
                print("Cannot print packet " + args[0])
            else:
                for header in packet_data.headers:
                    print(header.name + ":")
                    for field in header.fields:
                        field_bytes = field.value

                        # In python2.X this is a str, so we need to map each char to its
                        # integer equivalent.
                        # In python3.X its bytes, which is already a sequence of ints
                        if type(field_bytes) == str:
                            field_bytes = map(ord, field_bytes)

                        print("  " + field.name + ": " + ':'.join(hex(n)[2:].zfill(2).upper() for n in field_bytes))
                    print("")

        elif len(args) == 2 and args[0] == "raw" and args[1].isdigit():
            msg_type, packet_data = self.debugger.get_raw_packet(int(args[1]))

            if msg_type == PFPSimDebugger_pb2.DebugMsg.GenericAcknowledge:
                print("Cannot print packet " + args[1])
            else:
                raw_packet = packet_data.value

                hexdump(raw_packet)

        elif len(args) in (3,4) and args[0] == "field" and args[2].isdigit():

            #print("Looking up field " + args[1] + " for packet id " + args[2])

            msg_type, packet_data = self.debugger.get_packet_field(int(args[2]), args[1])

            if msg_type == PFPSimDebugger_pb2.DebugMsg.GenericAcknowledge:
                print("Cannot print packet " + args[2])
            else:
                field_bytes = packet_data.value

                # In python2.X this is a str, so we need to map each char to its
                # integer equivalent.
                # In python3.X its bytes, which is already a sequence of ints
                if type(field_bytes) == str:
                    field_bytes = map(ord, field_bytes)

                fmt = args[3] if len(args) == 4 else 'hex'

                fmt = 'hex' if fmt == 'ip4' and len(field_bytes) != 4 else fmt

                if fmt == 'hex':
                    print(':'.join(hex(n)[2:].zfill(2).upper() for n in field_bytes))
                elif fmt == 'dec':
                    print(reduce(lambda x,y: (x*0x100)+y, field_bytes))
                elif fmt == 'ip4':
                    print('.'.join(map(str, field_bytes)))
                else:
                    raise BadInputException("print")

        else:
            raise BadInputException("print")

    # continue command - continues simulation after break
    @handle_bad_input
    def do_continue(self, line):
        '''
continue <time> <units>
c <time> <units>
    Use this command after the simulation has stopped due to a breakpoint or watchpoint to continue the execution. An
    optional time and unit can be given to continue the simulation only for a given amount of time.
    Supported units:
        ns (nanoseconds)
        us (microseconds)
        ms (milliseconds)
        s (seconds)
        m (minutes)
        h (hours)
        '''

        if self.run_called is True and self.sim_ended is False:
            args = line.split(" ")
            if args[0] != '':
                time = args[0]
                unit = args[1]
                time_final = self.getTimeInNS(time, unit)
                msg_type, reply = self.debugger.continue_(time_final)
            else:
                msg_type, reply = self.debugger.continue_()
            self.handleRunOrContinueReply(msg_type, reply)
        else:
            if self.run_called is False:
                print("Simulation has not been started. Use 'Run' command to start simulation.")
            elif self.sim_ended is True:
                print("Simulation has ended. Use 'restart' command to start simulation from the beginning.")

    # c command - same as continue
    def do_c(self, line):
        '''
continue <time> <units>
c <time> <units>
    Use this command after the simulation has stopped due to a breakpoint or watchpoint to continue the execution. An
    optional time and unit can be given to continue the simulation only for a given amount of time.
    Supported units:
        ns (nanoseconds)
        us (microseconds)
        ms (milliseconds)
        s (seconds)
        m (minutes)
        h (hours)
        '''

        self.do_continue(line)

    # next command
    @handle_bad_input
    def do_next(self, line):
        '''
next
n
    Use this command to continue the simulation until the current packet leaves the current module or enters the next
    module. The current packet is defined by the whoami command.
        '''
        if len(line.split(" ")) == 1 and line.split(" ")[0] == '':
            if self.run_called:
                msg_type, reply = self.debugger.next()
                self.handleRunOrContinueReply(msg_type, reply);
            else:
                print("Simulation has not been started. Use 'Run' command to start simulation.")
        else:
            raise BadInputException("next")

    # n command - same as next
    def do_n(self, line):
        '''
next
n
    Use this command to continue the simulation until the current packet leaves the current module or enters the next
    module. The current packet is defined by the whoami command.
        '''

        self.do_next(line)

    # break command - set breakpoints
    @handle_bad_input
    def do_break(self, line):
        '''
break <conditions> <options>
    Set a breakpoint on a module, packet and/or time. Multiple conditions and options can be combined. There must be a
    minimum of one condition.

    conditions:
        -m <module_name>
            Sets a breakpoint on the module with given name. Simulation will stop when a packet enters the given module.
        -p <packet_id>
            Sets a breakpoint on the packet with given id. Simulation will stop when the given packet enters any module.
        -t <time> <unit>
            Sets a breakpoint at the given time. Simulation will stop at or at the first read after the given time.
            Breakpoints with this condition will always be temporary. That is, they will be deleted after being hit.
            Supported units:
                ns (nanoseconds)
                us (microseconds)
                ms (milliseconds)
                s (seconds)
                m (minutes)
                h (hours)
        dropped_packet
            Break when a packet is dropped.

    options:
        --temp
            Creates a temporary breakpoint, which will be deleted once it is hit.
        --disable
            Creates a breakpoint that is disabled. It will not be hit until it is enabled using the 'enable' command.
        '''

        args = line.split(" ")
        i = 0
        conditions = []
        values = []
        temp = False
        disabled = False
        if len(args) == 1 and args[0] == '':
            raise BadInputException("break")

        if len(args) == 1 and args[0] == "dropped_packet":
            self.debugger.break_on_packet_drop()
            print("Breakpoint was set successfully.")
            return

        while (i < len(args)):
            if args[i] == "-m" or args[i] == "-m_in":
                conditions.append(PFPSimDebugger_pb2.BREAK_ON_MODULE_READ)
                values.append(args[i + 1])
                i += 1
            elif args[i] == "-m_out":
                conditions.append(PFPSimDebugger_pb2.BREAK_ON_MODULE_WRITE)
                values.append(args[i + 1])
                i += 1
            elif args[i] == "-p":
                conditions.append(PFPSimDebugger_pb2.BREAK_ON_PACKET_ID)
                if args[i + 1].isdigit():
                    values.append(args[i + 1])
                else:
                    raise BadInputException("break")
                i += 1
            elif args[i] == "-t":
                try:
                    conditions.append(PFPSimDebugger_pb2.BREAK_AT_TIME)
                    time = args[i + 1]
                    unit = args[i + 2]
                    time_final = self.getTimeInNS(time, unit)
                    values.append(time_final)
                    i += 2
                except:
                    raise BadInputException("break")
            elif args[i] == "--temp":
                temp = True
            elif args[i] == "--disable":
                disabled = True
            else:
                raise BadInputException("break")
            i += 1

        msg_type, reply = self.debugger.set_breakpoint(conditions, values, temp, disabled)
        if(reply == PFPSimDebugger_pb2.GenericAcknowledgeMsg.SUCCESS):
            print("Breakpoint was set successfully.")
        else:
            print("Breakpoint could not be set.")

    # tbreak command - shortcut to set temporary breakpoint
    def do_tbreak(self, line):
        '''
tbreak <conditions> <options>
    Set a temporary breakpoint on a module, packet and/or time. Temporary breakpoints are automatically deleted once
    they are hit. Multiple conditions and options can be combined. There must be a minimum of one condition.

    conditions:
        -m <module_name>
            Sets a breakpoint on the module with given name. Simulation will stop when a packet enters the given module.
        -p <packet_id>
            Sets a breakpoint on the packet with given id. Simulation will stop when the given packet enters any module.
        -t <time> <unit>
            Sets a breakpoint at the given time. Simulation will stop at or at the first read after the given time.
            Supported units:
                ns (nanoseconds)
                us (microseconds)
                ms (milliseconds)
                s (seconds)
                m (minutes)
                h (hours)

    options:
        -- disable
            Creates a breakpoint that is disabled. It will not be hit until it is enabled using the 'enable' command.
        '''

        line = line + " --temp"
        self.do_break(line)

    # watch command - set watchpoint
    @handle_bad_input
    def do_watch(self, line):
        '''
watch counter <counter_name> <options>
watch -c <counter_name> <options>
    Set a watchpoint on the given counter. The user will be notified every time the given counter's value changes.
    Auto-completion for the counter name is supported.

    options:
        --disable
            Creates a watchpoint that is disabled. It will not be hit until it is enabled using the 'enable' command.
        '''

        args = line.split(" ")
        if len(args) == 2 or len(args) == 3:
            if args[0] == "counter" or args[0] == "-c":
                counter_name = args[1]
                if len(args) == 3:
                    if args[2] == "--disable":
                        disabled = True
                    else:
                        raise BadInputException("watch")
                else:
                    disabled = False
                msg_type, reply = self.debugger.set_watchpoint(counter_name, disabled)
                if reply == PFPSimDebugger_pb2.GenericAcknowledgeMsg.SUCCESS:
                    print("Watchpoint was set successfully.")
                else:
                    print("Watchpoint could not be set.")
            else:
                raise BadInputException("watch")
        else:
            raise BadInputException("watch")

    # enable command - enable breakpoint or watchpoint
    @handle_bad_input
    def do_enable(self, line):
        '''
enable break <breakpoint_id>
    Enable the breakpoint with the given ID. Use 'all' for the id to enable all breakpoints.

enable watch <watchpoint_id>
    Enable the watchpoint with the given ID. Use 'all' for the id to enable all watchpoints.
        '''
        args = line.split(" ")
        if len(args) != 2:
            raise BadInputException("enable")

        if args[0] == "break":
            if args[1] == "all":
                bkpts = self.debugger.get_breakpoints()
                for ident in bkpts.id_list:
                    self.debugger.enable_breakpoint(ident)
            else:
                try:
                    reply = self.debugger.enable_breakpoint(args[1])
                except:
                    raise BadInputException("enable")
        elif args[0] == "watch":
            if args[1] == "all":
                wps = self.debugger.get_watchpoints()
                for ident in wps.id_list:
                    self.debugger.enable_watchpoint(ident)
            else:
                try:
                    reply = self.debugger.enable_watchpoint(args[1])
                except:
                    raise BadInputException("enable")
        else:
            raise BadInputException("enable")

    # disable command - disable breakpoint or watchpoint
    @handle_bad_input
    def do_disable(self, line):
        '''
disable break <breakpoint_id>
    Disable the breakpoint with the given ID. Use 'all' for the id to disable all breakpoints.

disable watch <watchpoint_id>
    Disable the watchpoint with the given ID. Use 'all' for the id to disable all watchpoints.
        '''

        args = line.split(" ")
        if len(args) != 2:
            raise BadInputException("disable")

        if args[0] == "break":
            if args[1] == "all":
                bkpts = self.debugger.get_breakpoints()
                for ident in bkpts.id_list:
                    self.debugger.disable_breakpoint(ident)
            else:
                try:
                    reply = self.debugger.disable_breakpoint(args[1])
                except:
                    raise BadInputException("disable")
        elif args[0] == "watch":
            if args[1] == "all":
                wps = self.debugger.get_watchpoints()
                for ident in wps.id_list:
                    self.debugger.disable_watchpoint(ident)
            else:
                try:
                    reply = self.debugger.disable_watchpoint(args[1])
                except:
                    raise BadInputException("disable")
        else:
            raise BadInputException("disable")


    # backtrace command - get trace of given packet (whoami is default)
    @handle_bad_input
    def do_backtrace(self, line):
        '''
backtrace <packet_id>
bt <packet_id>
    Prints the list of modules the given packet has gone through as well as the read time (time it entered the module),
    write time (time it exited the module) and delta (time it spend within the module). If no packet id is given, the
    current packet's ID will be used as defined by the whoami command.
        '''

        args = line.split(" ")
        packet_id = args[0]
        if packet_id != '':
            try:
                msg_type, reply = self.debugger.backtrace(int(packet_id))
            except:
                raise BadInputException("backtrace")
        else:
            msg_type, reply = self.debugger.backtrace()
        if msg_type == PFPSimDebugger_pb2.DebugMsg.GenericAcknowledge and reply == PFPSimDebugger_pb2.GenericAcknowledgeMsg.FAILED:
            print("Could not get backtrace for packet " + packet_id)
        else:
            print("Backtrace for packet " + str(reply.packet_id) + ":")
            table = []
            for i, mod in enumerate(reply.module_list):
                read_time = reply.read_time_list[i]
                write_time = reply.write_time_list[i]
                if read_time != -1 and write_time != -1:
                    delta = float(write_time - read_time)
                else:
                    delta = ""
                if read_time == -1:
                    read = ""
                else:
                    read = float(read_time)
                if write_time == -1:
                    write = ""
                else:
                    write = float(write_time)
                table.append([mod, read, write, delta])

            print(tabulate(table, headers=["Module Name", "Read Time (ns)", "Write Time (ns)", "Delta (ns)"]))

    # bt command - same as backtrace
    def do_bt(self, line):
        '''
backtrace <packet_id>
bt <packet_id>
    Prints the list of modules the given packet has gone through as well as the read time (time it entered the module),
    write time (time it exited the module) and delta (time it spend within the module). If no packet id is given, the
    current packet's ID will be used as defined by the whoami command.
        '''

        self.do_backtrace(line)


    # info command - get information about current debug session
    @handle_bad_input
    def do_info(self, line):
        '''
info breakpoints
info break
    Prints the list of breakpoints that are currently set. It indicates their ID, if they are temporary and their
    conditions.

info watchpoints
info watch
    Prints the list of watchpoints that are currently set. It indicates their ID and the counter name they are set on.

info ignore
    Prints the list of modules that are currently being ignored.
        '''

        args = line.split(" ")

        if len(args) > 1:
            raise BadInputException("info")

        if args[0] == "breakpoints" or args[0] == "break":
            reply = self.debugger.get_breakpoints()
            # Prints all breakpoints!
            print("Breakpoint List:")
            for i, bkpt in enumerate(reply.breakpoint_condition_list):
                if reply.temporary[i] == "1":
                    temp = "Yes"
                else:
                    temp = "No"

                if reply.disabled[i] == "1":
                    enabled = "No"
                else:
                    enabled = "Yes"

                print(str(reply.id_list[i]) + " - Temporary: " + temp + ", Enabled: " + enabled)
                for j, condition in enumerate(bkpt.condition_list):
                    if condition == PFPSimDebugger_pb2.BREAK_ON_MODULE_READ:
                        print("    Enter Module: " + bkpt.value_list[j])
                    elif condition == PFPSimDebugger_pb2.BREAK_ON_MODULE_WRITE:
                        print("    Leave Module: " + bkpt.value_list[j])
                    elif condition == PFPSimDebugger_pb2.BREAK_ON_PACKET_ID:
                        print("    Packet: " + bkpt.value_list[j])
                    elif condition == PFPSimDebugger_pb2.BREAK_AT_TIME:
                        print("    Time: " + bkpt.value_list[j] + " ns")

        elif args[0] == "watchpoints" or args[0] == "watch":
            reply = self.debugger.get_watchpoints()
            # Print all watchpoints
            print("Watchpoint List:")
            for i, wp_id in enumerate(reply.id_list):
                if reply.disabled[i] == "0":
                    enabled = "Yes"
                else:
                    enabled = "No"
                print(str(wp_id) + " - Counter Name: " + reply.name_list[i] + ", Enabled: " + enabled)
        elif args[0] == "ignore":
            reply = self.debugger.get_ignore_modules();
            # Print all ignored modules
            table = []
            for mod in reply.module_list:
                table.append([mod])
            print(tabulate(table, headers=["Ignored Modules"]))
        else:
            raise BadInputException("info")

    # delete command - delete breakpoint or watchpoint
    @handle_bad_input
    def do_delete(self, line):
        '''
delete break <breakpoint_id>
    Delete the breakpoint with the given ID. Use 'all' for the id to delete all breakpoints. Use 'dropped_packet' to
    stop breaking when a packet is dropped.

delete watch <watchpoint_id>
    Delete the watchpoint with the given ID. Use 'all' for the id to delete all watchpoints.

delete ignore <module_name>
    Stop ignoring the given module. Use 'all' for the module name to stop ignoring all modules. Auto-completion is
    supported for the module name.
        '''

        args = line.split(" ")

        if len(args) != 2:
            raise BadInputException("delete")

        if args[0] == "break":
            if args[1] == "all":
                bkpts = self.debugger.get_breakpoints()
                for ident in bkpts.id_list:
                    self.debugger.delete_breakpoint(ident)
            elif args[1] == "dropped_packet":
                self.debugger.delete_break_on_packet_drop()
            elif args[1].isdigit():
                    try:
                        reply = self.debugger.delete_breakpoint(args[1])
                    except:
                        raise BadInputException("delete")
            else:
                raise BadInputException("delete")
        elif args[0] == "watch":
            if args[1] == "all":
                wps = self.debugger.get_watchpoints()
                for ident in wps.id_list:
                    self.debugger.delete_watchpoint(ident)
            elif args[1].isdigit():
                try:
                    reply = self.debugger.delete_watchpoint(args[1])
                except:
                    raise BadInputException("delete")
            else:
                raise BadInputException("delete")
        elif args[0] == "ignore":
            if args[1] == "all":
                pass
            else:
                msg_type, reply = self.debugger.delete_ignore_module(args[1])
        else:
            raise BadInputException("delete")

    # whoami command - get which packet you're current following
    @handle_bad_input
    def do_whoami(self, line):
        '''
whoami
    Prints the ID of the packet that is currently being followed. This corresponds to the packet on which the breakpoint
    hit. This may not always be defined.
        '''

        if len(line.split(" ")) == 1 and line.split(" ")[0] == '':
            reply = self.debugger.whoami()
            if reply.packet_id == -1:
                print("whoamoi is not determined.")
            else:
                print("Packet ID: " + str(reply.packet_id))
        else:
            raise BadInputException("whoami")

    # ignore command - indicates that the user does not want to get notications for the specified module
    @handle_bad_input
    def do_ignore(self, line):
        '''
ignore <module_name>
    Ignore all notications from a given module. The simulation will not stop on this module and any packets within the
    module will not be listed when using the print packets command.
        '''
        args = line.split(" ")
        if len(args) == 1 and args[0] != '':
            module = args[0]
            msg_type, reply = self.debugger.ignore_module(module)
        else:
            raise BadInputException("ignore")

    # whattimeisit command - returns current simulation time
    @handle_bad_input
    def do_whattimeisit(self, line):
        '''
whattimeisit
    Get the current simulation time.
        '''
        args = line.split(" ")
        if len(args) > 1 or (len(args) == 1 and args[0] != ''):
            raise BadInputException("whattimeisit")
        else:
            time = self.debugger.get_simulation_time()
            print("Simulation Time: " + str(time) + " ns")

    # quit command - quit debugger. Kills child process.
    @handle_bad_input
    def do_quit(self, line):
        '''
quit
q
    Kill the simulation and exit the PFPSimDebugger.
        '''

        if len(line.split(" ")) == 1 and line.split(" ")[0] == '':
            self.debugger.quit()
            return True
        else:
            raise BadInputException("quit")

    # q command - same as quit
    def do_q(self, line):
        '''
quit
q
    Kill the simulation and exit the PFPSimDebugger.
        '''

        return self.do_quit(line)

    # EOF command (ctrl-d) - same as quit
    def do_EOF(self, line):
        '''
EOF (ctrl-d)
    Kill the simulation and exit the PFPSimDebugger.
        '''

        print('')
        return self.do_quit(line)

    # clear command
    @handle_bad_input
    def do_clear(self, line):
        '''
clear
    Clear the screen.
        '''

        if len(line.split(" ")) == 1 and line.split(" ")[0] == '':
            subprocess.call('clear')
        else:
            raise BadInputException("clear")

    # Control Plane Commands
    @handle_bad_input
    def do_cp(self, line):
        '''
cp <command>
    Send a command to the control plane agent.
    See possible commands below:

insert_entry <table_name> <match_key> <action_name> <action_data>
    Inserts a new entry into the specified table. Note that any changes to the match action tables are not instantanenous as these do not bypass the simulation. Thus, the simulation must run a certain
    amount of time before changes are reflected. There can be multiple action data.

modify_entry <table_name> <handle> <action_name> <action_data>
    Modifies an existing table entry. Note that any changes to the match action tables are not instantanenous as these do not bypass the simulation. Thus, the simulation must run a certain amount of
    time before changes are reflected. There can be multiple action data.

delete_entry <table_name> <handle>
    Deletes an existing table entry. Note that any changes to the match action tables are not instantanenous as these do not bypass the simulation. Thus, the simulation must run a certain amount of
    time before changes are reflected. There can be multiple action data.
        '''

        if len(line) > 0:
            try:
                command = line
                self.debugger.cp_command(command);
            except:
                raise BadInputException("cp")
        else:
            raise BadInputException("cp")

    @handle_bad_input
    def do_table_dump(self, line):
        '''
table_dump <table_name>
    Prints out the contents of a table. If no table name is given, all tables will be printed.
        '''

        args = line.split(" ")
        num = len(args)
        if num > 1:
            raise BadInputException("table_dump")
        else:
            table_name = args[0]
            final_table = []
            entries = self.debugger.get_table_entries()
            headings = ["Table", "Action", "Match Key", "Handle", "Action Data", "Status"]
            for table, action_dict in entries.items():
                if table_name == '' or table_name == table:
                    l = [table]
                    i = 0
                    for action, entry_list in action_dict.items():
                        if i != 0:
                            l = ['']
                        l.append(action)
                        j = 0
                        for entry in entry_list:
                            if j != 0:
                                l = ['','']
                            match_key = ", ".join(entry['match_key'])
                            action_data = ", ".join(entry['action_data'])

                            entry_status = "NONE"
                            if entry['status'] == PFPSimDebugger_pb2.TableEntriesMsg.OK:
                                entry_status = "OK"
                            elif entry['status'] == PFPSimDebugger_pb2.TableEntriesMsg.INSERTING:
                                entry_status = "INSERTING"
                            elif entry['status'] == PFPSimDebugger_pb2.TableEntriesMsg.DELETING:
                                entry_status = "DELETING"
                            elif entry['status'] == PFPSimDebugger_pb2.TableEntriesMsg.MODIFYING:
                                entry_status = "MODIFYING"

                            l.extend([match_key, entry['handle'], action_data, entry_status])
                            final_table.append(l)
                            j += 1
                        i += 1

            print(tabulate(final_table, headers=headings))

    # Auto complete for print command
    def complete_print(self, text, line, begidx, endidx):
        args = line.split(" ")
        PRINT_OPTIONS = ('counter', 'packets', 'dropped_packets')
        FLAGS = ('-c', '-p')
        if args[1] in PRINT_OPTIONS or args[1] in FLAGS:
            if args[1] == 'counter' or args[1] == '-c':
                names, values = self.debugger.print_all_counters()
                names.append('all')
                return [i for i in names if i.startswith(text)]
            elif args[1] == 'packets' or args[1] == '-p':
                pass
        else:
            return [i for i in PRINT_OPTIONS if i.startswith(text)]

    # Auto complete for restart command
    def complete_restart(self, text, line, begidx, endidx):
        RESTART_OPTIONS = ('clean',)
        return [i for i in RESTART_OPTIONS if i.startswith(text)]

    # Auto complete for watch command
    def complete_watch(self, text, line, begidx, endidx):
        WATCH_OPTIONS = ('counter',)
        args = line.split(" ")
        if args[1] in WATCH_OPTIONS:
            if args[1] == 'counter':
                names, values = self.debugger.print_all_counters()
                return [i for i in names if i.startswith(text)]
        else:
            return [i for i in WATCH_OPTIONS if i .startswith(text)]

    # Auto complete for break command
    def complete_break(self, text, line, begidx, endidx):
        BREAK_OPTIONS = ('dropped_packet',)
        return [i for i in BREAK_OPTIONS if i.startswith(text)]

    # Auto complete for info command
    def complete_info(self, text, line, begidx, endidx):
        INFO_OPTIONS = ('break', 'watch', 'ignore')
        return [i for i in INFO_OPTIONS if i.startswith(text)]

    # Auto complete for delete command
    def complete_delete(self, text, line, begidx, endidx):
        DELETE_OPTIONS = ('break', 'watch', 'ignore')
        args = line.split(" ")
        if args[1] in DELETE_OPTIONS:
            if args[1] == 'break':
                DELETE_BREAK_OPTIONS = ('dropped_packet', 'all')
                return [i for i in DELETE_BREAK_OPTIONS if i.startswith(text)]
            elif args[1] == 'watch':
                DELETE_WATCH_OPTIONS = ('all',)
                return [i for i in DELETE_WATCH_OPTIONS if i.startswith(text)]
            elif args[1] == 'ignore':
                reply = self.debugger.get_ignore_modules()
                return [i for i in reply.module_list if i.startswith(text)]
        else:
            return [i for i in DELETE_OPTIONS if i.startswith(text)]

    # Auto complete for enable command
    def complete_enable(self, text, line, begidx, endidx):
        ENABLE_OPTIONS = ('break', 'watch')
        return [i for i in ENABLE_OPTIONS if i.startswith(text)]

    # Auto complete for disable command
    def complete_disable(self, text, line, begidx, endidx):
        DISABLE_OPTIONS = ('break', 'watch')
        return [i for i in DISABLE_OPTIONS if i.startswith(text)]

    def handleRunOrContinueReply(self, msg_type, reply):
        if msg_type == PFPSimDebugger_pb2.DebugMsg.BreakpointHit:
            if reply.read == "1":
                read_write = "Read"
            else:
                read_write = "Write"
            print("\033[0mBreakpoint Hit - ID: " + str(reply.id) + "\nPacket ID: " + str(reply.packet_id) + "\nModule: " + reply.module + " (" + read_write + ")\nTime: " + str(reply.time_ns) + " ns")
        elif msg_type == PFPSimDebugger_pb2.DebugMsg.WatchpointHit:
            print("\033[0mWatchpoint Hit - ID: " + str(reply.id) + "\nCounter Name: " + reply.counter_name + "\nCounter Value: " + str(reply.old_value) + " -> " + str(reply.new_value))
        elif msg_type == PFPSimDebugger_pb2.DebugMsg.SimulationEnd:
            print("\033[0mSimulation has ended.")
            self.sim_ended = True
        elif msg_type == PFPSimDebugger_pb2.DebugMsg.SimulationStopped:
            if reply.read is True:
                read_str = "Read"
            else:
                read_str = "Write"
            print("\033[0mPacket ID: " + str(reply.packet_id) + "\nModule: " + reply.module + " (" + read_str + ")\nTime: " + str(reply.time) + " ns")
        elif msg_type == PFPSimDebugger_pb2.DebugMsg.PacketDropped:
            print("\033[0mPacket Dropped!\nPacket ID: " + str(reply.packet_id) + "\nModule: " + reply.module + "\nReason: " + reply.reason)
        elif msg_type == PFPSimDebugger_pb2.DebugMsg.GenericAcknowledge:
            pass

    def getTimeInNS(self, time_str, unit):
        time_double = float(time_str)
        if unit == 's':
            time_double_ns = time_double * (10 ** 9)
            time_final = str(time_double_ns)
        elif unit == 'ms':
            time_double_ns = time_double * (10 ** 6)
            time_final = str(time_double_ns)
        elif unit == 'us':
            time_double_ns = time_double * (10 ** 3)
            time_final = str(time_double_ns)
        elif unit == 'ns':
            time_final = str(time_double)
        elif unit == 'm':
            time_double_ns = time_double * 60 * (10 ** 9)
            time_final = str(time_double_ns)
        elif unit == 'h':
            time_double_ns = time_double * 3600 * (10 ** 9)
            time_final = str(time_double_ns)
        return time_final

def start_simulation():
    print("Launching " + exe_name + " as child process...")

    # Put together list with command to execute and its arguments
    popen_input = ['./' + exe_name]
    popen_input.extend(arg_list)
    popen_input.append('-d')

    if verbose is False:
        FNULL = open(os.devnull, 'w')
        return subprocess.Popen(popen_input, stdin=subprocess.PIPE, stdout=FNULL)
    else:
        return subprocess.Popen(popen_input, stdin=subprocess.PIPE)

def main():
    try:
        argparser = argparse.ArgumentParser(description="Debugger for PFPSim")
        argparser.add_argument('-v', action='store_true', help="Verbose Mode")
        argparser.add_argument('--debug', action='store_true', help="PFPDB Debug Mode")
        argparser.add_argument('-a', action='store_true', help=argparse.SUPPRESS) # Attach to existing simulation
        argparser.add_argument('--args', action='store', type=str, help="Arguments which must be passed to executable.", required=True)
        argparser.add_argument('exe_path')
        # argparser.add_argument('--json', help='JSON description of P4 program', type=str, action="store", required=True)
        args = argparser.parse_args()
        global verbose
        if args.v:
            verbose = True
        else:
            verbose = False

        global arg_list
        arg_list = []
        if args.args:
            arg_list = args.args.strip(" ").split(" ")

        exe_path = args.exe_path
        if os.path.exists(exe_path):
            global exe_name
            exe_name = exe_path.split("/")[-1]
            exe_dir = exe_path[:-len(exe_name)]
            if exe_dir is '':
                exe_dir = './'
            os.chdir(exe_dir)
        else:
            print("error: " + exe_path + " was not found.")
            sys.exit(1)

        attach = False
        if args.a:
            try:
                pid = subprocess.check_output(["pidof", exe_name])
                attach = True
                print("Attached to " + exe_name + " (PID: " + str(pid.rstrip('\n')) + ")")
            except:
                print("Process " + exe_name + " does not exist")
                sys.exit(1)
        else:
            exit_flag = False;
            try:
                pid_tmp = subprocess.check_output(["pidof", exe_name])
                print("A process with the name " + exe_name + " is already running. Please kill this other process to proceed.")
                exit_flag = True;
            except:
                pass
            if exit_flag is True:
                sys.exit(1)

        # load_json(args.json)
        # print(TABLES['forward'].actions['set_dmac'].runtime_data)

        # Suppress SystemC Copyright message
        os.environ["SYSTEMC_DISABLE_COPYRIGHT_MESSAGE"] = "1"

        global p
        if not attach:
            p = start_simulation()
            pid = p.pid
        else:
            p = None

        ipc_url = "ipc:///tmp/pfpsimdebug.ipc"
        ipc_session = DebuggerIPCSession(ipc_url)
        debugger = PFPSimDebugger(ipc_session, p, pid, args.debug)
        debugger_cmd = PFPSimDebuggerCmd(debugger)
        debugger_cmd.cmdloop()
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
        if p.poll() == None:
            p.kill()
    except Exception as e:
        print(str(e))
        traceback.print_exc()
        if 'p' in globals():
            if p.poll() == None:
                p.kill()
