This is the document which outlines the communication protocols for the STAC5-IP-E120. Use this to navigate the pdf documents in this folder. Each pdf has its corresponding page numbers in the file name ex: Host-Command-Reference - p151-200.pdf contains pages 151-200 of the whole Host-Command document. Each file also contains the same content chart you see below.

---

# QUICK REFERENCE: Commands Used in This Project

**NOTE FOR AI ASSISTANTS:** This section contains all the SCL commands used by `src/stac5_manager.py`. You do NOT need to read the PDF files for normal development - all required command details are documented here.

## eSCL Protocol (Ethernet Communication)

- **TCP Port:** 7776 (recommended - reliable)
- **UDP Port:** 7775 (alternative)
- **Packet Format:** `[0x00, 0x07]` + ASCII command + `[0x0D]` (carriage return)
- **Response Format:** Same header + ASCII response + CR, or just ASCII with `%` (success) or `?` (error)

Example packet for "ME" (Motor Enable):
```
Bytes: 0x00 0x07 0x4D 0x45 0x0D
       [header] [ M ][ E ][CR]
```

## Motion Commands

| Command | Name | Description | Example |
|---------|------|-------------|---------|
| **ME** | Motor Enable | Enables the motor driver | `ME` |
| **MD** | Motor Disable | Disables the motor driver | `MD` |
| **SD** | Set Direction | Sets jog direction. **SD0** = CW/positive, **SD1** = CCW/negative. **Only affects jogging, not FL moves.** | `SD0` or `SD1` |
| **JS** | Jog Speed | Sets jog velocity in rev/sec. **MUST use decimal format. Only positive values - use SD for direction.** | `JS2.0` |
| **CJ** | Commence Jogging | Starts jogging at the speed set by JS | `CJ` |
| **SJ** | Stop Jogging | Stops jogging with deceleration | `SJ` |
| **VE** | Velocity | Sets velocity for point-to-point moves in rev/sec. **MUST use decimal format.** | `VE1.5` |
| **DI** | Distance | Sets distance for moves in steps. **Accepts SIGNED values for direction control.** | `DI4000` or `DI-4000` |
| **FL** | Feed to Length | Executes a move using current VE and DI settings | `FL` |
| **ST** | Stop | Stops motion with controlled deceleration | `ST` |
| **SK** | Stop & Kill | Emergency stop - immediate halt, clears buffer | `SK` |

### IMPORTANT FORMAT NOTES
- **JS and VE MUST include decimal point**: `JS2.0` works, `JS2` returns error `?`
- **JS does NOT accept negative values**: Returns error `?5`
- **DI ACCEPTS signed values**: `DI2000` = positive, `DI-2000` = negative
- **SD COMMAND DOES NOT WORK** on STAC5-IP-E120: Returns `?` error

### CRITICAL: Unsupported Commands on STAC5-IP-E120
The following commands return `?` error and are NOT supported:
- **SD** (Set Direction) - Cannot use SD0/SD1 for jog direction
- **JM** (Jog Mode) - Not available
- **ZS, ZE, ZA** (Network Watchdog) - Not available

**Solution for jogging**: Use **DI** to set direction before CJ:
- DI1 + CJ = jog in positive direction
- DI-1 + CJ = jog in negative direction
- SJ = stop jogging
- This gives smooth continuous jogging in both directions!

### Jog Sequence Example (DI-based, since SD doesn't work)
```
# Jog POSITIVE direction:
DI1             # Set direction positive (just 1 step, but sets direction flag)
JS2.0           # Set jog speed (MUST have decimal)
CJ              # Commence jogging (smooth continuous motion)
...             # (motor runs until stopped)
SJ              # Stop jogging

# Jog NEGATIVE direction:
DI-1            # Set direction negative
JS2.0           # Set jog speed
CJ              # Commence jogging
...
SJ              # Stop jogging
```

### Move Sequence Example (direction via signed DI)
```
VE1.5    # Set velocity to 1.5 rev/sec (MUST have decimal)
DI-4000  # Set distance to -4000 steps (negative = CCW)
FL       # Execute the move
```

## Configuration Commands

| Command | Name | Description | Example |
|---------|------|-------------|---------|
| **AC** | Acceleration | Sets acceleration rate in rev/sec² | `AC10.0` |
| **DE** | Deceleration | Sets deceleration rate in rev/sec² | `DE10.0` |

## Status Commands (Immediate/Query)

| Command | Name | Description | Response Example |
|---------|------|-------------|------------------|
| **EP** | Encoder Position | Returns current encoder position in steps | `EP=12345` |
| **IP** | Immediate Position | Returns commanded position in steps | `IP=12345` |
| **IV** | Immediate Velocity | Returns current velocity | `IV=0.00` |
| **SC** | Status Code | Returns drive status as hex code | `SC=0001` |
| **AL** | Alarm Code | Returns alarm status as hex code | `AL=0000` |
| **AR** | Alarm Reset | Clears any active alarms | `%` (success) |

### Status Code (SC) Bit Definitions
- Bit 0 (0x0001): Motor Enabled
- Bit 1 (0x0002): Sampling (in motion)
- Bit 2 (0x0004): Drive Fault
- Bit 3 (0x0008): In Position
- Bit 4 (0x0010): Moving
- Bit 5 (0x0020): Jogging
- Bit 6 (0x0040): Stopping
- Bit 7 (0x0080): Waiting
- Bit 8 (0x0100): Saving
- Bit 9 (0x0200): Alarm Present
- Bit 10 (0x0400): Homing
- Bit 11 (0x0800): Wait for Input
- Bit 12 (0x1000): Motion Command Processing
- Bit 13 (0x2000): In Q Program
- Bit 14 (0x4000): Initializing
- Bit 15 (0x8000): Reserved

### Common Alarm Codes (AL)
- `0000`: No alarm
- `0002`: Position Limit
- `0004`: CCW Limit
- `0008`: CW Limit
- `0010`: Over Temp
- `0020`: Internal Voltage Fault
- `0040`: Over Voltage
- `0080`: Under Voltage
- `0100`: Over Current
- `0200`: Open Motor Winding
- `0400`: Bad Encoder
- `0800`: Communication Error
- `1000`: Bad Flash
- `2000`: No Move
- `4000`: Reserved
- `8000`: Reserved

## Info Commands

| Command | Name | Description | Response Example |
|---------|------|-------------|------------------|
| **RV** | Revision Level | Returns firmware revision | `RV=102` |
| **MV** | Model & Version | Returns model info | `MV=102I083` |

## Response Characters
- `%` - Command accepted/success
- `?` - Command error/rejected
- `*` - Command buffered (for buffered commands)

## Python Usage (from stac5_manager.py)

```python
# Build packet
def build_packet(command: str) -> bytes:
    HEADER = bytes([0x00, 0x07])
    CR = bytes([0x0D])
    return HEADER + command.encode('ascii') + CR

# Example: Jog right (positive) at 2 rev/sec
# NOTE: SD doesn't work on STAC5-IP, use DI to set direction instead
send_command("DI1")          # Set direction positive (1 step)
send_command("JS2.0")        # Jog speed (MUST have decimal!)
send_command("CJ")           # Commence jogging (smooth continuous)
# ... later ...
send_command("SJ")           # Stop jogging

# Example: Jog left (negative) at 2 rev/sec
send_command("DI-1")         # Set direction negative (-1 step)
send_command("JS2.0")        # Jog speed
send_command("CJ")           # Commence jogging
# ... later ...
send_command("SJ")           # Stop jogging

# Example: Move 4000 steps positive (use signed DI)
send_command("VE1.5")  # Velocity 1.5 rev/sec (MUST have decimal!)
send_command("DI4000") # Positive distance = positive direction
send_command("FL")     # Execute move

# Example: Move 4000 steps negative (use signed DI)
send_command("VE1.5")  # Velocity
send_command("DI-4000") # Negative distance = negative direction
send_command("FL")     # Execute move

# Example: Read encoder
response = send_command("EP")  # Returns "EP=12345" or "EP=-12345"
```

---

# Full Command Reference (PDF Navigation) 

Host Command Reference
Contents
Getting Started..................................................................................11
Servo Drives.....................................................................................11
StepSERVO......................................................................................11
Stepper Drives..................................................................................11
Commands.......................................................................................13
Buffered Commands.........................................................................13
Stored Programs in Q Drives............................................................................13
Multi-tasking in Q Drives..................................................................................13
Immediate Commands......................................................................13
Using Commands...............................................................................13
Commands in Q drives.....................................................................14
SCL Utility software...........................................................................15
Command Summary..........................................................................16
Motion Commands............................................................................17
Servo Commands.............................................................................18
Configuration Commands.................................................................19
Communications Commands............................................................21
Register Commands.........................................................................21
I/O Commands..................................................................................22
Q Program Commands.....................................................................23
Command Listing...............................................................................24
AC - Acceleration Rate......................................................................25
AD - Analog Deadband......................................................................26
AD - Analog Deadband (SV200 Drives).............................................27
AF - Analog Filter...............................................................................28
AG - Analog Velocity Gain..................................................................29
AI - Alarm Reset Input ......................................................................30
AL - Alarm Code................................................................................33
AM - Max Acceleration.......................................................................36
AN - Analog Torque Gain...................................................................37
AO - Alarm Output.............................................................................38
AP - Analog Position Gain.................................................................40
AR - Alarm Reset (Immediate)...........................................................41
AS - Analog Scaling...........................................................................42
AT - Analog Threshold........................................................................43
AV - Analog Offset Value....................................................................44
AV - Analog Offset Value - SV200......................................................45
AX - Alarm Reset (Buffered)..............................................................46
AZ - Analog Zero...............................................................................47
3 920-0002 Rev. W
7/6/2021
Host Command Reference
BD - Brake Disengage Delay.............................................................48
BE - Brake Engage Delay..................................................................49
BO - Brake Output.............................................................................50
BR - Baud Rate .................................................................................52
BS - Buffer Status..............................................................................53
CA - Change Acceleration Current....................................................54
CB - CANopen Baudrate....................................................................55
CC - Change Current.........................................................................56
CD - Idle Current Delay Time.............................................................58
CE - Communication Error.................................................................59
CF - Anti-resonance Filter Frequency................................................60
CG - Anti-resonance Filter Gain.........................................................61
CI - Change Idle Current....................................................................62
CJ - Commence Jogging...................................................................64
CM - Command Mode (AKA Control Mode)......................................65
CN - Secondary Control Mode...........................................................67
CO - Node ID/ IP address..................................................................68
CP - Change Peak Current................................................................69
CR - Compare Registers ...................................................................70
CS - Change Speed...........................................................................71
CT - Continue.....................................................................................72
DA - Define Address..........................................................................73
DC - Change Distance.......................................................................74
DD - Default Display Item of LEDs.....................................................75
DE - Deceleration...............................................................................76
DI - Distance/Position........................................................................77
DL - Define Limits..............................................................................78
DL - Define Limits (StepSERVO and SV200 drives)..........................80
DR - Data Register for Capture..........................................................81
DS - Switching Electronic Gearing.....................................................82
DW - Dumping Voltage Setting...........................................................83
ED - Encoder Direction......................................................................84
EF - Encoder Function.......................................................................85
EG - Electronic Gearing.....................................................................87
EH - Extended Homing......................................................................88
EI - Input Noise Filter.........................................................................90
EN - Numerator of Electronic Gearing Ratio......................................91
EP - Encoder Position........................................................................92
ER - Encoder Resolution...................................................................93
920-0002 Rev.W 4
7/6/2021
Host Command Reference
ES - Single-Ended Encoder Usage...................................................94
ES - Absolute Encoder Mode ...........................................................95
EU - Denominator of Electronic Gearing Ratio..................................96
FA - Function of the Single-ended Analog Input................................97
FC - Feed to Length with Speed Change..........................................98
FD - Feed to Double Sensor..............................................................100
FE - Follow Encoder..........................................................................101
FH - Find Home.................................................................................102
FI - Filter Input...................................................................................105
FL - Feed to Length...........................................................................109
FM - Feed to Sensor with Mask Distance..........................................110
FO - Feed to Length and Set Output.................................................111
FP - Feed to Position.........................................................................112
FS - Feed to Sensor...........................................................................113
FX - Filter select inputs......................................................................114
FY - Feed to Sensor with Safety Distance.........................................115
GC - Current Command.....................................................................116
GG - Controller Global Gain Selection...............................................117
HA - Homing Acceleration..................................................................118
HC – Hard Stop Current....................................................................119
HD - Hard Stop Fault Delay...............................................................120
HG - 4th Harmonic Filter Gain...........................................................121
HL - Homing Deceleration..................................................................122
HO – Home Offset.............................................................................123
HP - 4th Harmonic Filter Phase.........................................................124
HS - Hard Stop Homing.....................................................................125
HV - Homing Velocity.........................................................................127
HW - Hand Wheel..............................................................................128
Immediate Status Commands...........................................................129
IA - Immediate Analog.......................................................................130
IC - Immediate Current (Commanded)..............................................132
ID - Immediate Distance....................................................................133
IE - Immediate Encoder.....................................................................134
IF - Immediate Format.......................................................................135
IH - Immediate High Output...............................................................136
IL - Immediate Low Output.................................................................137
IO - Output Status..............................................................................138
IP - Immediate Position......................................................................140
IQ - Immediate Current (Actual).........................................................141
5 920-0002 Rev. W
7/6/2021
Host Command Reference
IS - Input Status.................................................................................142
IT - Immediate Temperature...............................................................145
IU - Immediate Voltage.......................................................................147
IV - Immediate Velocity......................................................................148
IX - Immediate Position Error.............................................................149
JA - Jog Acceleration.........................................................................150
JC - Velocity (Oscillator) mode second speed...................................151
JC - 8 Jog Velocities (SV200 drives)..................................................152
JD - Jog Disable.................................................................................153
JE - Jog Enable..................................................................................154
JL - Jog Decel....................................................................................155
JM - Jog Mode...................................................................................156
JS - Jog Speed..................................................................................157
KC - Overall Servo Filter....................................................................158
KD - Differential Constant..................................................................159
KE - Differential Filter.........................................................................160
KF - Velocity Feedforward Constant...................................................161
KG – Secondary Global Gain............................................................162
KI - Integrator Constant......................................................................163
KJ - Jerk Filter Frequency..................................................................164
KK - Inertia Feedforward Constant....................................................165
KP - Proportional Constant................................................................166
KV - Velocity Feedback Constant.......................................................167
LA - Lead Angle Max Value................................................................168
LM - Software Limit CCW..................................................................170
LP - Software Limit CW......................................................................171
LS - Lead Angle Speed......................................................................172
LV - Low Voltage threshold.................................................................173
MC - Motor Current, Rated................................................................174
MD - Motor Disable............................................................................175
ME - Motor Enable.............................................................................176
MN - Model Number..........................................................................177
MO - Motion Output...........................................................................178
MR - Microstep Resolution.................................................................181
MS - Control Mode Selection.............................................................182
MT - Multi-Tasking..............................................................................183
MV - Model & Revision......................................................................184
NO - No Operation.............................................................................187
OF - On Fault.....................................................................................188
920-0002 Rev.W 6
7/6/2021
Host Command Reference
OI - On Input......................................................................................189
OP - Option board..............................................................................190
PA - Power-up Acceleration Current..................................................191
PB - Power-up Baud Rate .................................................................193
PC - Power-up Current.......................................................................194
PD - In-Position Counts.....................................................................195
PE - In-Position Timing......................................................................196
PF - Position Fault..............................................................................197
PH - Inhibit Pulse Command ............................................................198
PI - Power-up Idle Current.................................................................199
PK - Parameter Lock..........................................................................200
PL - Position Limit..............................................................................201
PM - Power-up Mode.........................................................................202
PN - Probe On Demand.....................................................................203
PP - Power-up Peak current...............................................................204
PR - Protocol.....................................................................................205
PS - Pause.........................................................................................206
PT - Pulse Type..................................................................................207
PV - Secondary Electronic Gearing...................................................208
PW - Password..................................................................................209
QC - Queue Call................................................................................210
QD - Queue Delete............................................................................211
QE - Queue Execute..........................................................................212
QG - Queue Goto..............................................................................213
QJ - Queue Jump...............................................................................214
QK - Queue Kill..................................................................................215
QL - Queue Load...............................................................................216
QR - Queue Repeat...........................................................................217
QS - Queue Save...............................................................................218
QU - Queue Upload...........................................................................219
QX - Queue Load & Execute.............................................................220
RC - Register Counter.......................................................................221
RD - Register Decrement...................................................................223
RE - Restart or Reset........................................................................224
RI - Register Increment......................................................................225
RL - Register Load - immediate.........................................................226
RM - Register Move...........................................................................227
RO - Anti-Resonance ON..................................................................228
RR - Register Read...........................................................................229
RS - Request Status..........................................................................230
7 920-0002 Rev. W
7/6/2021
Host Command Reference
RU - Register Upload.........................................................................231
RV - Revision Level............................................................................232
RW - Register Write...........................................................................233
RX - Register Load - buffered............................................................234
R+ - Register Add..............................................................................235
R- - Register Subtract........................................................................236
R* - Register Multiply.........................................................................237
R/ - Register Divide............................................................................238
R& - Register AND.............................................................................239
R| - Register OR................................................................................240
SA - Save Parameters.......................................................................241
SC - Status Code...............................................................................242
SD - Set Direction..............................................................................243
SF - Step Filter Frequency.................................................................244
SH - Seek Home................................................................................245
SI - Enable Input Usage.....................................................................246
SJ - Stop Jogging .............................................................................248
SK - Stop & Kill..................................................................................249
SM - Stop Move.................................................................................250
SO - Set Output.................................................................................251
SP - Set Position................................................................................252
SS - Send String................................................................................253
ST - Stop............................................................................................254
TD - Transmit Delay...........................................................................255
TI - Test Input.....................................................................................256
TO - Tach Output................................................................................257
TR - Test Register..............................................................................259
TS - Time Stamp................................................................................260
TT - Pulse Complete Timing..............................................................261
TV - Torque Ripple.............................................................................262
VC - Velocity Change.........................................................................263
VE - Velocity.......................................................................................264
VI - Velocity Integrator Constant........................................................265
VL - Voltage Limit...............................................................................266
VM - Maximum Velocity......................................................................267
VP - Velocity Mode Proportional Constant.........................................268
VR - Velocity Ripple...........................................................................269
WD - Wait Delay.................................................................................270
WI - Wait for Input..............................................................................271
920-0002 Rev.W 8
7/6/2021
Host Command Reference
WM - Wait on Move............................................................................272
WP - Wait Position.............................................................................273
WT - Wait Time..................................................................................274
ZA – Network Communication Time-out (Watchdog) Action..............274
ZC - Regen Resistor Continuous Wattage.........................................275
ZE - Network Communication Time-Out (Watchdog) Enable.............276
ZR - Regen Resistor Value................................................................277
ZS- Network Communication Time-out (Watchdog) Delay................278
ZT - Regen Resistor Peak Time.........................................................279
Data Registers..................................................................................280
Read-Only data registers..................................................................280
Read/Write data registers.................................................................280
User-Defined data registers..............................................................280
Storage data registers.......................................................................280
Using Data Registers.........................................................................281
Loading (RL, RX)..............................................................................281
Uploading (RL, RU)...........................................................................281
Writing Storage registers (RW) (Q drives only).................................282
Reading Storage registers (RR) (Q drives only)...............................282
Moving data registers (RM) (Q drives only)......................................282
Incrementing/Decrementing (RI, RD) (Q drives only).......................282
Counting (RC, “I” register) (Q drives only)........................................282
Math & Logic (R+, R-, R*, R/, R&, R|) (Q drives only)......................282
Conditional Testing (CR, TR) (Q drives only)....................................283
Data Register Assignments..............................................................283
Read-Only data registers: a - z.........................................................283
Read/Write data registers: A - Z.......................................................288
User-Defined data registers: 0 - 9, other characters.........................292
Appendices.......................................................................................293
Appendix A: Non-Volatile Memory in Q drives................................294
Appendix B: Host Serial Communications......................................295
Appendix C: Host Serial Connections..............................................299
Appendix D: The PR Command.........................................................303
Appendix E: Alarm and Status Codes..............................................312
Appendix F: Working with Inputs and Outputs...............................320
Appendix G: eSCL (SCL over Ethernet) Reference.........................328
Appendix H: EtherNet/IP....................................................................342
Input Assembly (0x64)......................................................................344
Input Assembly (0x65) .....................................................................346
9 920-0002 Rev. W
7/6/2021
Host Command Reference
Input Status Details ..........................................................................346
Output Assembly (0x70) ..................................................................347
Explicit Messaging............................................................................354
Type 2 Message Format...................................................................360
Table 1: Message Type 1 Command List.........................................364
Table 2: Message Type 2 Commands..............................................369
Table 3: Parameter read/write operands..........................................370
IO Encoding Table.............................................................................373
Register Encoding Table...................................................................374
EtherNet/IP And Q Programs............................................................376
EtherNet/IP on large networks..........................................................378
Appendix I: Troubleshooting.............................................................379
Appendix J: List of Supported Drives..............................................381
Appendix K: Modbus appendix.........................................................388
What is Modbus?..............................................................................390
Wiring................................................................................................390
Drive Behavior..................................................................................391
Monitoring.........................................................................................391
Sending Commands.........................................................................391
Examples..........................................................................................392
SCL Command Mode Table..............................................................393
IO Encoding Table.............................................................................394
Register Encoding Table...................................................................395
Modbus Register Table for Step Drives.............................................398
Modbus Register Table for Servo Drives...........................................406
Modbus Register Table for StepSERVO Drives.................................416
