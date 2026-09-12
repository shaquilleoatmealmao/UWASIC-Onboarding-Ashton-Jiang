# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import FallingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    # Write your test here
    clock = Clock(dut.clk, 100, unit="ns") #this clock has a period of 100 ns, which is 10 MHz
    cocotb.start_soon(clock.start())  # Starts the clock
    dut.ena.value = 1 #turns on the PWM module
    dut.ui_in.value = ui_in_logicarray(1, 0, 0) #sets the initial ncs to be 1 which is off, COPI to be 0 and SCLK to be 0
    dut.rst_n.value = 0 # sets the reset to be 0, which means that the module will be in reset state
    await ClockCycles(dut.clk, 5) #wait for 5 active clock edges so everything has time to reset
    dut.rst_n.value = 1 #so rst_n is not reset, so if you initial not reset then it will not reset
    await ClockCycles(dut.clk, 5) #wait another 5 clock cyclesso that it has time to come out of reset
    await send_spi_transaction(dut, 1, 0x00, 0x01) # this is a write transaction, so it will write to the address 0x00 and the data is 0x01, which means that the output will be enabled
    await send_spi_transaction(dut, 1, 0x02, 0x01) #this transaction goes to the address 0x02 and then turns it on, so the output will be inabled and the frequency will be 1 Hz
    await send_spi_transaction(dut, 1, 0x04, 0x80) #it is writing 8, which is half of the hex 128 that is the full space of the reg which means that the pwm will be 50%
    await RisingEdge(dut.uo_out[0])
    first_rise_ns = cocotb.utils.get_sim_time(unit="ns")

    await RisingEdge(dut.uo_out[0])
    second_rise_ns = cocotb.utils.get_sim_time(unit="ns")

    period_ns = second_rise_ns - first_rise_ns
    frequency_hz = 1_000_000_000 / period_ns
    dut._log.info(f"Measured PWM frequency: {frequency_hz:.2f} Hz")
    assert 2970 <= frequency_hz <= 3030, (
        f"Expected PWM frequency around 3000 Hz, got {frequency_hz:.2f} Hz"
    )

@cocotb.test()
async def test_pwm_duty(dut):
    clock = Clock(dut.clk, 100, unit="ns")
    cocotb.start_soon(clock.start())
    dut.ena.value = 1 #turns on the PWM module
    dut.ui_in.value = ui_in_logicarray(1, 0, 0) #sets the initial ncs to be 1 which is off, COPI to be 0 and SCLK to be 0
    dut.rst_n.value = 0 # sets the reset to be 0, which means that the module will be in restart state
    await ClockCycles(dut.clk, 5) #wait for 5 active clock edges so everything has time to reset
    dut.rst_n.value = 1 #so rst_n is not reset
    await ClockCycles(dut.clk, 5) #wait another 5 clock cyclesso that it has time to come out of reset
    await send_spi_transaction(dut, 1, 0x00, 0x01)
    await send_spi_transaction(dut, 1, 0x02, 0x01)
    await send_spi_transaction(dut, 1, 0x04, 0x80)
    await RisingEdge(dut.uo_out[0])
    rise_1_ns = cocotb.utils.get_sim_time(unit="ns")

    await FallingEdge(dut.uo_out[0])
    fall_ns = cocotb.utils.get_sim_time(unit="ns")

    await RisingEdge(dut.uo_out[0])
    rise_2_ns = cocotb.utils.get_sim_time(unit="ns")

    high_time_ns = fall_ns - rise_1_ns
    low_time_ns = rise_2_ns - fall_ns
    measured_duty_cycle = high_time_ns / (high_time_ns + low_time_ns) * 100



    dut._log.info(f"Measured PWM duty cycle: {measured_duty_cycle:.2f}%")
    expected_duty_percent = (0x80 / 256) * 100
    assert abs(measured_duty_cycle - expected_duty_percent) <= 1.0, (
        f"Expected about {expected_duty_percent:.2f}% duty cycle, "
        f"got {measured_duty_cycle:.2f}%"
    )

    await send_spi_transaction(dut, 1, 0x04, 0x00)

    for _ in range(5):
        await ClockCycles(dut.clk, 1000)
        assert dut.uo_out[0].value == 0, (
            "Expected PWM output to remain low for duty cycle 0x00"
        )

    await send_spi_transaction(dut, 1 , 0x04, 0xFF) #more like wait until this actionn here finishes
    for _ in range(5):
        await ClockCycles(dut.clk, 1000)
        assert dut.uo_out[0].value == 1, (
            "Expected PWM output to remain high for duty cycle 0xFF"
        )

    await send_spi_transaction (dut, 1, 0x04, 0x00)
    for _ in range(5):
        await ClockCycles(dut.clk, 1000)
        assert dut.uo_out[0].value == 0, (
            "Expected PWM output to remain low for duty cycle 0x00"
        )