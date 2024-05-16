# ulp_compiler
A very-light-weight compiler for ESP32 ULP, pure cpython/micropython code and easy to use

Don't want to install and configure complex toolchains for a few lines of code running on a very simple FSM? This pure python/micropython single file tool will meet the requirements for compiling ULP code. It's small enough to be embedded in micropython codes for run-time compiling.

At present, I have only done the work above ESP32S2 because I need to, and a simple modification should also be used for other ESP32 series MCUs.

## ESP32S2/s2ulp.py

Usage:

```sh
python s2ulp.py <ASM file name> <binary file name>
```	
Example:

```sh
python s2ulp.py a.s a.bin
```

### Description

it's for ESP32S2 and basically all the features have been implemented, including the high 16-bit half-word LD/ST, but some details of the ST usage have not been implemented.

See `_opcodes` inside it for supported FSM codes, or modify it for other ESP32 MCUs. (Be careful, the technical manual is not always correct, and I have found errors in my ESP32S2 TRM V1.1, Chapter 1.5.2.2, about Rsrc/Rdst.)

There can only one ASM code per line (labels like 'l123:' can be included).

.data and .bss sections are not supported now. And in fact they are not useful for micropython. IDF users can also access data directly by using the memory address.

NOTICE, it's important. there's a big direffent from other standard asemble compiler, labels, address and offsets are all expressed as 32-bit words, not bytes. This is also the internal address expression of ULP, and here I didn't do complex translations to adapt to the way of bytes address.

### Example

ASM code:

```asm
start:
    jump entry
data:
    .long 0
    .long 0
.set to_add, 1
entry:
    move r3, data
    ld r0, r3, 1 # address/offset must be expressed as 32-bit words, not bytes
    add r0, r0, to_add
    jumpr add1-pc, 100, gt # support 'pc' for relative jump
    move r0, 0
add1:
    st r0, r3, 1
    halt
```

And in Micropython:

```python
from esp32 import ULP
import time
ulp=ULP()
ulp.set_wakeup_period(0, 500000)
# this way
if 1:
	with open('example.bin', 'rb') as f:
	ulp.load_binary(0, f.read())
# or this way
else:
	import s2ulp
	ulp.load_binary(0, s2ulp.link(s2ulp.asm('''
		... ASM source ... 
	''')))
ulp.run(0)
from machine import mem32
while True:
print(mem32[0x50000004])
time.sleep(1)
```

### More example

See `a.asm`, which is the code I'm using that provides debounced counter, rotary encoder and button functions (including click and long press events).

And in Micropython, following is the a snippet of code, which shows how to open RTCIO for input.

```python
_ULP_BASE=const(0x3F408000)
_RTC_BASE=const(0x50000000)
_PIN_LEFT_SPD=12 # for ESP32S2, RTCIO number is same as GPIO number

# SENS_SAR_IO_MUX_CONF_REG, this should be set after all pins have been initialized. 
# And then do not call machine.Pin() for initialize new Pin any more.
mem32[_ULP_BASE+0x944]=0x80000000 
# RTCIO_TOUCH_PADn_REG, enable RTCIO input, pull-up
mem32[_ULP_BASE+0x484+_PIN_LEFT_SPD*4]=(1<<19)|(1<<13)|(1<<27)
```
