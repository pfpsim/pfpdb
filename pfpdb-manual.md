# PFPSIM Debugger User Manual

Table of Contents:
- [PFPSIM Debugger User Manual](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#pfpsim-debugger-user-manual)
 - [Quitting the Debugger](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#quitting-the-debugger)
 - [Controlling the Simulation](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#controlling-the-simulation)
   - [Run the simulation](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#run-the-simulation)
    - [Restarting the Simulation:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#restarting-the-simulation)
    - [Resuming Simulation:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#resuming-simulation)
    - [Stepping though breakpoints:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#stepping-though-breakpoints)
 - [Observing Simulation Variables](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#observing-simulation-variables)
   - [Counters:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#counters)
    - [Packets:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#packets)
      - [Filters:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#filters)
    - [Dropped Packets:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#dropped-packets)
    - [Backtrace:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#backtrace)
    - [Current Module (PE/CE):](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#current-module-pece)
    - [Current Simulation Time:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#current-simulation-time)
 - [Breakpoints, Watchpoints and Ignore Modules](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#breakpoints-watchpoints-and-ignore-modules)
   - [Creating Breakpoints:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#creating-breakpoints)
    - [Breakpoint conditions:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#breakpoint-conditions)
      - [Break on a module:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#break-on-a-module)
      - [Break on a Packet:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#break-on-a-packet)
      - [Break on a give time:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#break-on-a-give-time)
    - [Breakpoint Options:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#breakpoint-options)
    - [Temporary Breakpoint:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#temporary-breakpoint)
    - [Disable a breakpoint:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#disable-a-breakpoint)
    - [Break on Dropped Packets:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#break-on-dropped-packets)
    - [Creating a Temporary Breakpoint:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#creating-a-temporary-breakpoint)
      - [Breakpoint conditions:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#breakpoint-conditions)
        - [Break on a module:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#break-on-a-module)
        - [Break on a Packet:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#break-on-a-packet)
        - [Break on a give time:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#break-on-a-give-time)
     - [Watchpoint:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#watchpoint)
        - [Options:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#options)
    - [Ignoring notifications:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#ignoring-notifications)
    - [Debugger session status:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#debugger-session-status)
    - [Deleting Break/Watch points:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#deleting-breakwatch-points)
    - [Disabling Break/Watch points:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#disabling-breakwatch-points)
    - [Enabling Disabled Break/Watch points:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#enabling-disabled-breakwatch-points)
 - [Control Plane Operations](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#control-plane-operations)
   - [Inserting an entry:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#inserting-an-entry)
    - [Modifying an entry:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#modifying-an-entry)
    - [Deleting an entry:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#deleting-an-entry)
    - [Print match tables:](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#print-match-tables)
 - [Other](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#other)
   - [Clear the screen](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#clear-the-screen)
    - [Help within the debugger](https://github.com/pfpsim/pfpdb/blob/master/pfpdb-manual.md#help-within-the-debugger)

## Quitting the Debugger

```quit ```

``` q ```

Kill the simulation and exit the PFPSimDebugger.

## Controlling the Simulation

### Run the simulation

`run < time > < units >`

`r < time > < units >`

Use this command to start the simulation from within the PFPSimDebugger. If a time and unit is given, the simulation will run for the indicated amount of simulation time if it is not interrupted by a breakpoint hit. If not given, the simulation will run until completion or a breakpoint hit.

Supported units: ns (nanoseconds) us (microseconds) ms (milliseconds) s (seconds) m (minutes) h (hours)

### Restarting the Simulation:

`restart`

Use this command to restart the simulation from the beginning without removing any breakpoints or watchpoints.

`restart clean`

Use this command to restart the simulation from the beginning and remove the currently set breakpoints and watchpoints. It is equivalent to quitting the PFPSimDebugger and starting it again.

### Resuming Simulation:

`continue < time > < units > `

`c < time > < units > `

Use this command after the simulation has stopped due to a breakpoint or watchpoint to continue the execution. An optional time and unit can be given to continue the simulation only for a given amount of time. Supported units: ns (nanoseconds) us (microseconds) ms (milliseconds) s (seconds) m (minutes) h (hours)

### Stepping though breakpoints:

`next`
`n`

Use this command to continue the simulation until the current packet leaves the current module or enters the next module. The current packet is defined by the `whoami` command.


## Observing Simulation Variables

### Counters:

`print counter < counter_name > `

`print -c < counter_name >`

Print the value of the given counter. Use the name 'all' to print a list of all the counters within the simulation and their corresponding values. Auto-completion of the counter name is supported.

### Packets:

`print packets < filters > `

`print -p < filters > `

Print the list of packets that are currently in the simulation. The filters are optional.

#### Filters:
```
    -m < module_name >
        Will only print packets which are currently in the given module.
```

### Dropped Packets:

`print dropped_packets `

Print the list of packets that have been dropped.

### Backtrace:

`backtrace < packet_id > bt < packet_id > `

Prints the list of modules the given packet has gone through as well as the read time (time it entered the module), write time (time it exited the module) and delta (time it spend within the module). If no packet id is given, the current packet's ID will be used as defined by the `whoami` command.

### Current Module (PE/CE):

`whoami`

Prints the ID of the packet that is currently being followed. This corresponds to the packet on which the breakpoint hit. This may not always be defined.

### Current Simulation Time:

`whattimeisit`

Get the current simulation time.

## Breakpoints, Watchpoints and Ignore Modules

### Creating Breakpoints:

`break < conditions > < options >`

Set a breakpoint on a module, packet and/or time. Multiple conditions and options can be combined. There must be a minimum of one condition.

### Breakpoint conditions:

The following conditions for breaking can be specified when creating a breakpoint to describe its behavior.

Conditions can be compounded together for a breakpoint.

#### Break on a module:

```break -m < module_name > ```
 Sets a breakpoint on the module with given name. Simulation will stop when a packet enters the given module.

#### Break on a Packet:

```break -p < packet_id >```

Sets a breakpoint on the packet with given id. Simulation will stop when the given packet enters any module.

#### Break on a give time:

`break -t < time > < unit >`

Sets a breakpoint at the given time. Simulation will stop at or at the first read after the given time.

Breakpoints with this condition will always be temporary. That is, they will be deleted after being hit.

Supported units:
- ns (nanoseconds)
- us (microseconds)
- ms (milliseconds)
- s (seconds)
- m (minutes)
- h (hours)

### Breakpoint Options:

#### Temporary Breakpoint:
``` --temp ```

Creates a temporary breakpoint, which will be deleted once it is hit.

#### Disable a breakpoint:
```--disable ```

Creates a breakpoint that is disabled. It will not be hit until it is enabled using the 'enable' command.

### Break on Dropped Packets:

`break dropped_packet`

Break when a packet is dropped.

### Creating a Temporary Breakpoint:

`tbreak < conditions >`

Set a temporary breakpoint on a module, packet and/or time. Temporary breakpoints are automatically deleted once they are hit. Multiple conditions and options can be combined. There must be a minimum of one condition.

### Breakpoint conditions:

The following conditions for breaking can be specified when creating a breakpoint to describe its behavior.

Conditions can be compounded together for a breakpoint.

#### Break on a module:

```tbreak -m < module_name > ```
 Sets a breakpoint on the module with given name. Simulation will stop when a packet enters the given module.

#### Break on a Packet:

```tbreak -p < packet_id >```

Sets a breakpoint on the packet with given id. Simulation will stop when the given packet enters any module.

#### Break on a give time:

`tbreak -t < time > < unit >`

Sets a breakpoint at the given time. Simulation will stop at or at the first read after the given time.

Supported units:
- ns (nanoseconds)
- us (microseconds)
- ms (milliseconds)
- s (seconds)
- m (minutes)
- h (hours)

## Watchpoint:

`watch counter < counter_name > < options > `
`watch -c < counter_name > < options >`

Set a watchpoint on the given counter. The user will be notified every time the given counter's value changes. Auto-completion for the counter name is supported.

### Options:

`--disable`

Creates a watchpoint that is disabled. It will not be hit until it is enabled using the `enable` command.

## Ignoring notifications:

`ignore < module_name >`

Ignore all notifications from a given module. The simulation will not stop on this module and any packets within the module will not be listed when using the print packets command.

## Debugger session status:

`info`

breakpoints info break Prints the list of breakpoints that are currently set. It indicates their ID, if they are temporary and their conditions.

`info watchpoints`
`info watch`

Prints the list of watchpoints that are currently set. It indicates their ID and the counter name they are set on.

`info ignore`

Prints the list of modules that are currently being ignored.

## Deleting Break/Watch points:

`delete break < breakpoint_id >`

Delete the breakpoint with the given ID. Use 'all' for the id to delete all breakpoints. Use 'dropped_packet' to stop breaking when a packet is dropped.

`delete watch < watchpoint_id > `

Delete the watchpoint with the given ID. Use 'all' for the id to delete all watchpoints.

`delete ignore < module_name >`

Stop ignoring the given module. Use **'all'** for the module name to stop ignoring all modules. Auto-completion is supported for the module name.

## Disabling Break/Watch points:

`disable break < breakpoint_id >`

Disable the breakpoint with the given ID. Use 'all' for the id to disable all breakpoints.

`disable watch < watchpoint_id >`

Disable the watchpoint with the given ID. Use 'all' for the id to disable all watchpoints.

## Enabling Disabled Break/Watch points:

`enable break < breakpoint_id >`

Enable the breakpoint with the given ID. Use 'all' for the id to enable all breakpoints.

`enable watch < watchpoint_id >`

Enable the watchpoint with the given ID. Use 'all' for the id to enable all watchpoints.

## Control Plane Operations

### Inserting an entry:

`insert_entry < table_name > < match_key > < action_name > < action_data >`

Inserts a new entry into the specified table. Note that any changes to the match action tables are not instantanenous as these do not bypass the simulation.

Thus, the simulation must run a certain amount of time before changes are reflected. There can be multiple action data.

### Modifying an entry:

`modify_entry < table_name > < handle > < action_name > < action_data >`

Modifies an existing table entry. Note that any changes to the match action tables are not instantanenous as these do not bypass the simulation. Thus, the simulation must run a certain amount of time before changes are reflected. There can be multiple action data.

### Deleting an entry:

`delete_entry < table_name > < handle >`

Deletes an existing table entry. Note that any changes to the match action tables are not instantanenous as these do not bypass the simulation. Thus, the simulation must run a certain amount of time before changes are reflected. There can be multiple action data.

### Print match tables:

`table_dump < table_name > `

Prints out the contents of a table. If no table name is given, all tables will be printed.

## Other

### Clear the screen

`clear`

Clear the screen.

### Help within the debugger

`help < command >`

Prints help page for given command. If no command is given, the list of available commands is printed.
