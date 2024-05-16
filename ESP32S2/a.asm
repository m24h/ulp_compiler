# a ULP program to count motor cycles (per 1/4 cycle)
# and count rotary encoder steps
# its period is 500us 

start:
    jump entry
    
# for esp32 s2, RTCIO_RTC_GPIO_IN_REG, in 32-bit word
.set reg_io_in, (0x424>>2) 

# offset 4
state: 
    .long 0 # count of ULP invoked

# offset 8
left:  
    .long 0 # return address
    .long 0 # RTC IO number, must be in range 0-15
    .long 0 # count number, for every rising/falling
    .long 1 # last IO value
    .long 1 # last IO filtered value

# offset 28
right:
    .long 0 # return address
    .long 0 # RTC IO number, must be in range 0-15
    .long 0 # count number, for every rising/falling
    .long 1 # last IO value
    .long 1 # last IO filtered value
 
# offset 48
rotary:
    .long 0 # return addres
    .long 0 # RTC IO number of A pin, must be in range 0-15
    .long 0 # RTC IO number of B pin, must be in range 0-15
    .long 0 # count number, for every step of rotary encoder
    .long 1 # last A value
    .long 1 # last B value
    .long 0 # 0:B was changed, 1:A was changed

# offset 76
button:
    .long 0 # return address
    .long 0 # pin number, must be in range 0-15, and value 0 means button down
    .long 0 # event, 0:nothing 1:clicked 2:long-press 3:event is retrieved outside
    .long 0 # timer, 0:button is up state, >0: how many times button keeps in down state

entry:
    # process left
    move r3, left
    move r2, pc+3
    st   r2, r3, 0
    jump func_counter

    # process right
    move r3, right
    move r2, pc+3
    st   r2, r3, 0
    jump func_counter
    
    # process rotary
    move r3, rotary
    move r2, pc+3
    st   r2, r3, 0
    jump func_rotary
    
    # process button
    move r3, button
    move r2, pc+3
    st   r2, r3, 0
    jump func_button
    
    # increase state alive counter
    move r3, state
    ld   r0, r3, 0
    add  r0, r0, 1
    st   r0, r3, 0
    
    # all done
    halt
    halt
    halt
    halt

# count every rising/falling of RTC IO, IO value is double checked as filter
# r3 is the address of data stack, will not be changed
# data stack :
#    .long 0 # return addres
#    .long 0 # RTC IO number, must be in range 0-15
#    .long 0 # count number, for every rising/falling
#    .long 1 # last IO value
#    .long 1 # last IO filtered value
func_counter:
    # get IO value
    reg_rd reg_io_in, 25, 10
    ld   r1, r3, 1 
    rsh  r0, r0, r1 
    and  r0, r0, 1 
    # set it to last value and get the old last value
    ld   r1, r3, 3 
    st   r0, r3, 3
    # if they are not the same, return
    sub  r1, r1, r0
    jump func_counter_filtered, eq
    jump func_counter_done
func_counter_filtered:
    # set it to last filtered value and get the old last filtered value
    ld   r1, r3, 4
    st   r0, r3, 4
    # if they are the same, return
    sub  r1, r1, r0 
    jump func_counter_done, eq 
    # add 1 to counter
    ld   r0, r3, 2 
    add  r0, r0, 1 
    st   r0, r3, 2
func_counter_done:
    ld   r0, r3, 0
    jump r0
    
# count rotation for 1-pulse-every-1-step rotary encoder 
# r3 is the address of data stack, will not be changed
# data stack :
#    .long 0 # return addres
#    .long 0 # RTC IO number of A pin, must be in range 0-15
#    .long 0 # RTC IO number of B pin, must be in range 0-15
#    .long 0 # count number, for every step of rotary encoder
#    .long 1 # last A value
#    .long 1 # last B value
#    .long 0 # 0:A was changed, 1:B was changed
func_rotary:
    # get value of A (in r1), B (in r2)
    reg_rd reg_io_in, 25, 10
    ld    r1, r3, 1
    rsh   r1, r0, r1
    and   r1, r1, 1
    ld    r2, r3, 2
    rsh   r2, r0, r2
    and   r2, r2, 1    
    # check state
    ld    r0, r3, 6
    jumpr func_rotary_s1-pc, 1, eq
func_rotary_s0:      
    # check if B is toggled 
    ld    r0, r3, 5
    sub   r0, r0, r2
    jump  func_rotary_done, eq 
    # if B is toggled, store last A value, set state to 1
    st    r1, r3, 4
    move  r0, 1
    st    r0, r3, 6
    jump  func_rotary_done
func_rotary_s1: 
    # check if A is toggled 
    ld    r0, r3, 4
    sub   r0, r0, r1
    jump  func_rotary_done, eq 
    # if A is toggled, store last B value, set state to 0
    st    r2, r3, 5
    move  r0, 0
    st    r0, r3, 6
    # if A:0->1, increase/decrease counter according to B value
    or    r1, r1, r1
    jump  func_rotary_done, eq
    ld    r0, r3, 3
    add   r0, r0, r2
    add   r0, r0, r2
    sub   r0, r0, 1
    st    r0, r3, 3
func_rotary_done:
    ld    r0, r3, 0
    jump  r0

# get button event, clicked (debounced) or long pressed (2s for 500us calling period)
# r3 is the address of data stack, will not be changed
# data stack :
#    .long 0 # return address
#    .long 0 # pin number, must be in range 0-15, and value 0 means button down
#    .long 0 # event, 0:nothing 1:clicked 2:long-press 3:event is retrieved outside
#    .long 0 # timer, 0:button is up state, >0: how many times button keeps in down state
func_button:
    # get button value (in r1), current event (in r0)
    reg_rd reg_io_in, 25, 10
    ld    r1, r3, 1
    rsh   r1, r0, r1
    ld    r0, r3, 2
    and   r1, r1, 1
    jump  func_button_down, eq
func_button_up:
    # if event is retrieved outside, clear event
    jumpr func_button_up_cl_evt-pc, 3, eq
    # if event is not 0 and timer>0.05s (100*500us), set 'clicked' event
    jumpr func_button_up_done-pc, 0, gt
    ld    r0, r3, 3
    jumpr func_button_up_done-pc, 100, lt
    move  r0, 1
    st    r0, r3, 2
    jump  func_button_up_done
func_button_up_cl_evt:
    # clear event
    move  r0, 0
    st    r0, r3, 2 
func_button_up_done:
    # reset timer
    move  r0, 0
    st    r0, r3, 3
    jump  func_button_done
func_button_down:
    # if event is present, just return
    jumpr func_button_done-pc, 0, gt
    # increase timer
    ld    r0, r3, 3
    add   r0, r0, 1
    st    r0, r3, 3
    # if time>=2s (4000*500us), set long-press event
    jumpr func_button_done-pc, 4000, lt
    move  r0, 2
    st    r0, r3, 2
func_button_done:    
    ld    r0, r3, 0
    jump  r0    

should_not_reach_here:
    halt
    halt
    halt
    halt

