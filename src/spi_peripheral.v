`default_nettype none

module spi_peripheral (
    input  wire       clk,      // clock
    input  wire       rst_n,     // reset_n - low to reset
    input  wire       ncs, //the initiating relationship with peripheral
    input wire      sclk, //controller clock
    input wire      copi, //controller output, peripheral input

    output reg [7:0] en_reg_out_7_0, //output reg for the first 8 bits of output
    output reg [7:0] en_reg_out_15_8, //second 8 bits
    output reg [7:0] en_reg_pwm_7_0, //output for pwm
    output reg [7:0] en_reg_pwm_15_8,
    output reg [7:0] pwm_duty_cycle //output for the pwm duty cycle its the thing that deterines the percentage of time pwm is high or low
);

localparam [6:0] MAX_ADDRESS = 7'h04; //suggests that the the local parameter (something that can't change while circuit runs) is 4 and is 7 bits long and the max address for a register is 4

reg ncs_sync1; //its the thing that prevents metastability and being metastable is being bad basically
reg ncs_sync2;

reg sclk_sync1;
reg sclk_sync2;

reg copi_sync1;
reg copi_sync2;

reg ncs_prev; //previous value of ncs
reg sclk_prev; //previous value of sclk

wire ncs_fall; //can tell if the ncs rises or falls
wire ncs_rise;
wire sclk_rise;

assign ncs_fall = ncs_prev && !ncs_sync2; // basically says that if the previous was one and vurrent is 0 then it fell
assign ncs_rise = !ncs_prev && ncs_sync2; //if previous
assign sclk_rise = !sclk_prev && sclk_sync2;

reg [15:0] shift_reg; //shift the register in order to store data
reg [4:0] bit_count; //count the bits that have been shifted in, 32 digits of counting, basically 5 bits, we need to represent 16 bits, so 5 bits is enough to count to 16

always @(posedge clk or negedge rst_n) begin //basically it will run this thing either when the clock is posedge or when reset falls from 1 to 0, basically 0 is reset, 1 is normal, and in this case its 1 to 0, so actively resetting
    if (!rst_n) begin //like if reset is active
        shift_reg <= 16'h0000; //set the shift register to 0
        bit_count <= 5'd0; //set the bit count to 0
        ncs_prev <= 1'b0; //turn previous to 0
        sclk_prev <= 1'b0;
        ncs_sync1 <= 1'b0; //turn sync to 0
        ncs_sync2 <= 1'b0; //turn sync 2 to 0
        sclk_sync1 <= 1'b0; //turn sync 1 to
        sclk_sync2 <= 1'b0;
        copi_sync1 <= 1'b0;
        copi_sync2 <= 1'b0;

        en_reg_out_7_0 <= 8'h00; //this basically makes the registers blank
        en_reg_out_15_8 <= 8'h00;
        en_reg_pwm_7_0 <= 8'h00;
        en_reg_pwm_15_8 <= 8'h00;
        pwm_duty_cycle <= 8'h00;
    end

    else begin
        ncs_prev <= ncs_sync2;
        sclk_prev <= sclk_sync2;
        ncs_sync1 <= ncs; //sync the ncs signal to the clock domain of clk
        ncs_sync2 <= ncs_sync1; //then sync it agiain to make it metastable

        sclk_sync1 <= sclk; //same sync
        sclk_sync2 <= sclk_sync1;

        copi_sync1 <= copi;
        copi_sync2 <= copi_sync1;

        if (ncs_fall)
        begin //basically recognizing that when ncs drops, the process begins
            shift_reg <= 16'h0000; //reset the shift register to 0
            bit_count <=5'd0; //reset the bit count to 0;
        end
        else if (ncs_rise) //if ncs rises, then the process is done and we can write to the registers
        begin
            if ((bit_count == 5'd16 && (shift_reg[15] == 1'b1) && (shift_reg[14:8] <= MAX_ADDRESS))) //if the number of bits is 16 so like if the whole register is filled, if the first bit is a 1 so its a write command, and if the address is less than or equal to max address, then can we write to the registers.
            begin
                case (shift_reg[14:8]) //basically like a large acl that checks the shift_reg address bits for beng 00 and if it is ten it writes to the first register, if its like 01 then it writes to the seconf register
                    7'h00: en_reg_out_7_0 <= shift_reg[7:0]; //if the address is 0, then it will write to the first register
                    7'h01: en_reg_out_15_8 <= shift_reg[7:0];
                    7'h02: en_reg_pwm_7_0  <= shift_reg[7:0];
                    7'h03: en_reg_pwm_15_8 <= shift_reg[7:0];
                    7'h04: pwm_duty_cycle  <= shift_reg[7:0];
                    default:
                    begin
                        //do nothing if it isn't 00-04 which it shouldn't since we checked the max address earlier
                    end
                endcase
            end
        end
        else if (!ncs_sync2 && sclk_rise && (bit_count < 5'd16))
        begin
            shift_reg <= {shift_reg[14:0],copi_sync2}; //basically it takes the previous 0-14 bits and then a[ppends the new copi sync 2 bit and then shifts it into the shift reg
            bit_count <= bit_count + 1'b1; //increases the counter
        end


    end
end

endmodule