`default_nettype none

module tt_um_tiny_dram_pim (
  input  wire [7:0] ui_in,
  output wire [7:0] uo_out,
  input  wire [7:0] uio_in,
  output wire [7:0] uio_out,
  output wire [7:0] uio_oe,
  input  wire       ena,
  input  wire       clk,
  input  wire       rst_n
);
  localparam int NUM_CHANNELS = 2;
  localparam int ACC_WIDTH = 14;

  logic cmd_valid;
  logic [31:0] cmd_word;
  logic [3:0] decoded_op;
  logic decoded_ch;
  logic [2:0] decoded_subop;
  logic [1:0] decoded_precision;
  logic decoded_bank_a;
  logic decoded_bank_b;
  logic [1:0] decoded_row_a;
  logic [1:0] decoded_row_b;
  logic [2:0] decoded_flags;
  logic [7:0] decoded_imm8;
  logic rsp_valid [NUM_CHANNELS-1:0];
  logic [7:0] rsp_data [NUM_CHANNELS-1:0];
  logic [7:0] ch_status [NUM_CHANNELS-1:0];
  logic [31:0] rsp_word;
  logic spi_miso;
  logic [1:0] ch_bank_open [NUM_CHANNELS-1:0];
  logic ch_refresh_busy [NUM_CHANNELS-1:0];
  logic ch_refresh_bank [NUM_CHANNELS-1:0];
  logic [7:0] ch_bank0_data [NUM_CHANNELS-1:0];
  logic [7:0] ch_bank1_data [NUM_CHANNELS-1:0];
  logic [ACC_WIDTH-1:0] ch_acc [NUM_CHANNELS-1:0];

  logic pu_busy;
  logic [2:0] pu_busy_ctr;
  logic pu_ch;
  logic [1:0] pu_precision;
  logic pu_bank_a;
  logic pu_bank_b;
  logic [1:0] pu_lane;
  logic [1:0] pu_row_we;
  logic [1:0] pu_row_bank;
  logic [15:0] pu_row_data;
  logic [1:0] pu_acc_we;
  logic [2*ACC_WIDTH-1:0] pu_acc_data;
  logic [1:0] pu_error_set;

  localparam logic [3:0] OP_VOP    = 4'h5;
  localparam logic [3:0] OP_REDUCE = 4'h6;
  localparam logic [3:0] OP_ABORT  = 4'hc;
  localparam logic [1:0] PREC_INT1 = 2'b00;
  localparam logic [1:0] PREC_INT2 = 2'b01;
  localparam logic [1:0] PREC_INT4 = 2'b10;
  localparam logic [1:0] PREC_INT8 = 2'b11;
  localparam logic [2:0] VOP_XOR = 3'd0;
  localparam logic [2:0] VOP_ADD = 3'd1;
  localparam logic [2:0] REDUCE_DOT = 3'd0;
  localparam logic [2:0] REDUCE_MAC = 3'd1;

  // Decode every completed SPI frame once, then route it to one channel by the
  // decoded channel bit.
  command_decoder decoder (
    .cmd_word(cmd_word),
    .op(decoded_op),
    .ch(decoded_ch),
    .subop(decoded_subop),
    .precision(decoded_precision),
    .bank_a(decoded_bank_a),
    .bank_b(decoded_bank_b),
    .row_a(decoded_row_a),
    .row_b(decoded_row_b),
    .flags(decoded_flags),
    .imm8(decoded_imm8)
  );

  wire cmd_ch0 = cmd_valid && (decoded_ch == 1'b0);
  wire cmd_ch1 = cmd_valid && (decoded_ch == 1'b1);
  wire decoded_is_pim = (decoded_op == OP_VOP) || (decoded_op == OP_REDUCE);
  wire cmd_ch0_local = cmd_ch0 && !decoded_is_pim;
  wire cmd_ch1_local = cmd_ch1 && !decoded_is_pim;
  wire pu_busy_ch0 = pu_busy && (pu_ch == 1'b0);
  wire pu_busy_ch1 = pu_busy && (pu_ch == 1'b1);

  function automatic logic signed [8:0] sign_extend_lane (
    input logic [7:0] value,
    input logic [1:0] precision,
    input logic [1:0] lane
  );
    logic signed [3:0] lane4;
    begin
      lane4 = 4'sd0;
      unique case (precision)
        PREC_INT2: begin
          sign_extend_lane = {{7{value[(lane * 2) + 1]}}, value[lane * 2 +: 2]};
        end
        PREC_INT4: begin
          lane4 = value[lane * 4 +: 4];
          sign_extend_lane = {{5{lane4[3]}}, lane4};
        end
        default:   sign_extend_lane = 9'sd0;
      endcase
    end
  endfunction

  function automatic logic [7:0] lane_add_wrap (
    input logic [7:0] a,
    input logic [7:0] b,
    input logic [1:0] precision
  );
    logic [7:0] result;
    int lane;
    begin
      result = 8'h00;
      unique case (precision)
        PREC_INT2: begin
          for (lane = 0; lane < 4; lane = lane + 1) begin
            result[lane * 2 +: 2] = a[lane * 2 +: 2] + b[lane * 2 +: 2];
          end
        end
        PREC_INT4: begin
          for (lane = 0; lane < 2; lane = lane + 1) begin
            result[lane * 4 +: 4] = a[lane * 4 +: 4] + b[lane * 4 +: 4];
          end
        end
        default: result = 8'h00;
      endcase
      lane_add_wrap = result;
    end
  endfunction

  function automatic logic [ACC_WIDTH-1:0] popcount8 (
    input logic [7:0] value
  );
    logic [ACC_WIDTH-1:0] total;
    int bit_i;
    begin
      total = '0;
      for (bit_i = 0; bit_i < 8; bit_i = bit_i + 1) begin
        total = total + {{(ACC_WIDTH-1){1'b0}}, value[bit_i]};
      end
      popcount8 = total;
    end
  endfunction

  function automatic logic signed [ACC_WIDTH-1:0] dot_lane_term (
    input logic [1:0] precision,
    input logic [7:0] a,
    input logic [7:0] b,
    input logic [1:0] lane
  );
    logic signed [8:0] lane_a;
    logic signed [8:0] lane_b;
    begin
      if (precision == PREC_INT1) begin
        dot_lane_term = popcount8(a & b);
      end else begin
        lane_a = sign_extend_lane(a, precision, lane);
        lane_b = sign_extend_lane(b, precision, lane);
        dot_lane_term = lane_a * lane_b;
      end
    end
  endfunction

  function automatic logic [1:0] dot_last_lane (
    input logic [1:0] precision
  );
    begin
      unique case (precision)
        PREC_INT2: dot_last_lane = 2'd3;
        PREC_INT4: dot_last_lane = 2'd1;
        default:   dot_last_lane = 2'd0;
      endcase
    end
  endfunction

  function automatic logic [2:0] dot_latency (
    input logic [1:0] precision
  );
    begin
      unique case (precision)
        PREC_INT2: dot_latency = 3'd4;
        PREC_INT4: dot_latency = 3'd2;
        default:   dot_latency = 3'd1;
      endcase
    end
  endfunction

  wire [7:0] decoded_operand_a =
    decoded_ch ? (decoded_bank_a ? ch_bank1_data[1] : ch_bank0_data[1]) :
                 (decoded_bank_a ? ch_bank1_data[0] : ch_bank0_data[0]);
  wire [7:0] decoded_operand_b =
    decoded_ch ? (decoded_bank_b ? ch_bank1_data[1] : ch_bank0_data[1]) :
                 (decoded_bank_b ? ch_bank1_data[0] : ch_bank0_data[0]);
  wire [7:0] active_operand_a =
    pu_ch ? (pu_bank_a ? ch_bank1_data[1] : ch_bank0_data[1]) :
            (pu_bank_a ? ch_bank1_data[0] : ch_bank0_data[0]);
  wire [7:0] active_operand_b =
    pu_ch ? (pu_bank_b ? ch_bank1_data[1] : ch_bank0_data[1]) :
            (pu_bank_b ? ch_bank1_data[0] : ch_bank0_data[0]);
  wire [ACC_WIDTH-1:0] active_acc = pu_ch ? ch_acc[1] : ch_acc[0];
  wire [1:0] decoded_bank_open = decoded_ch ? ch_bank_open[1] : ch_bank_open[0];
  wire decoded_refresh_busy = decoded_ch ? ch_refresh_busy[1] : ch_refresh_busy[0];
  wire decoded_refresh_bank = decoded_ch ? ch_refresh_bank[1] : ch_refresh_bank[0];
  wire decoded_operands_ready = decoded_bank_open[decoded_bank_a] && decoded_bank_open[decoded_bank_b];
  wire decoded_operands_refreshing =
    decoded_refresh_busy && ((decoded_refresh_bank == decoded_bank_a) || (decoded_refresh_bank == decoded_bank_b));
  wire decoded_pim_valid =
    ((decoded_op == OP_VOP) &&
      (((decoded_subop == VOP_XOR)) ||
       ((decoded_subop == VOP_ADD) &&
        ((decoded_precision == PREC_INT2) || (decoded_precision == PREC_INT4))))) ||
    ((decoded_op == OP_REDUCE) &&
      ((decoded_subop == REDUCE_DOT) || (decoded_subop == REDUCE_MAC)) &&
      (decoded_precision != PREC_INT8));

  always_comb begin
    pu_row_we = 2'b00;
    pu_row_bank = 2'b00;
    pu_row_data = 16'h0000;
    pu_acc_we = 2'b00;
    pu_acc_data = '0;
    pu_error_set = 2'b00;

    if (pu_busy) begin
      if (pu_ch) begin
        pu_acc_we[1] = 1'b1;
        pu_acc_data[(2*ACC_WIDTH)-1:ACC_WIDTH] =
          active_acc + dot_lane_term(pu_precision, active_operand_a, active_operand_b, pu_lane);
      end else begin
        pu_acc_we[0] = 1'b1;
        pu_acc_data[ACC_WIDTH-1:0] =
          active_acc + dot_lane_term(pu_precision, active_operand_a, active_operand_b, pu_lane);
      end
      if (cmd_valid && decoded_is_pim) begin
        if (decoded_ch) begin
          pu_error_set[1] = 1'b1;
        end else begin
          pu_error_set[0] = 1'b1;
        end
      end
    end else if (cmd_valid && decoded_is_pim) begin
      if (!decoded_operands_ready || decoded_operands_refreshing || !decoded_pim_valid) begin
        if (decoded_ch) begin
          pu_error_set[1] = 1'b1;
        end else begin
          pu_error_set[0] = 1'b1;
        end
      end else if (decoded_op == OP_VOP) begin
        if (decoded_ch) begin
          pu_row_we[1] = 1'b1;
          pu_row_bank[1] = decoded_flags[0];
          if (decoded_subop == VOP_XOR) begin
            pu_row_data[15:8] = decoded_operand_a ^ decoded_operand_b;
          end else begin
            pu_row_data[15:8] = lane_add_wrap(decoded_operand_a, decoded_operand_b, decoded_precision);
          end
        end else begin
          pu_row_we[0] = 1'b1;
          pu_row_bank[0] = decoded_flags[0];
          if (decoded_subop == VOP_XOR) begin
            pu_row_data[7:0] = decoded_operand_a ^ decoded_operand_b;
          end else begin
            pu_row_data[7:0] = lane_add_wrap(decoded_operand_a, decoded_operand_b, decoded_precision);
          end
        end
      end else begin
        if (decoded_subop == REDUCE_DOT) begin
          if (decoded_ch) begin
            pu_acc_we[1] = 1'b1;
            pu_acc_data[(2*ACC_WIDTH)-1:ACC_WIDTH] = '0;
          end else begin
            pu_acc_we[0] = 1'b1;
            pu_acc_data[ACC_WIDTH-1:0] = '0;
          end
        end
      end
    end
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      pu_busy_ctr <= 3'd0;
      pu_ch <= 1'b0;
      pu_precision <= PREC_INT1;
      pu_bank_a <= 1'b0;
      pu_bank_b <= 1'b0;
      pu_lane <= 2'd0;
    end else begin
      if (cmd_valid && (decoded_op == OP_ABORT) && (decoded_ch == pu_ch)) begin
        pu_busy_ctr <= 3'd0;
        pu_lane <= 2'd0;
      end else if (pu_busy) begin
        pu_busy_ctr <= pu_busy_ctr - 3'd1;
        if ((pu_lane == dot_last_lane(pu_precision)) || (pu_busy_ctr == 3'd1)) begin
          pu_lane <= 2'd0;
        end else begin
          pu_lane <= pu_lane + 2'd1;
        end
      end else if (
        cmd_valid &&
        (decoded_op == OP_REDUCE) &&
        decoded_operands_ready &&
        !decoded_operands_refreshing &&
        decoded_pim_valid
      ) begin
        pu_busy_ctr <= dot_latency(decoded_precision);
        pu_ch <= decoded_ch;
        pu_precision <= decoded_precision;
        pu_bank_a <= decoded_bank_a;
        pu_bank_b <= decoded_bank_b;
        pu_lane <= 2'd0;
      end
    end
  end

  assign pu_busy = (pu_busy_ctr != 3'd0);

  // Channel refresh phases are staggered so the two banks do not request
  // autonomous refresh on the same core cycle after reset.
  pim_channel #(.REF_PHASE(0)) ch0 (
    .clk(clk),
    .rst_n(rst_n),
    .cmd_valid(cmd_ch0_local),
    .uop_op(decoded_op),
    .uop_subop(decoded_subop),
    .uop_bank_a(decoded_bank_a),
    .uop_row_a(decoded_row_a),
    .uop_imm8(decoded_imm8),
    .pim_busy_status(pu_busy_ch0),
    .pim_error_set(pu_error_set[0]),
    .pu_row_we(pu_row_we[0]),
    .pu_row_bank(pu_row_bank[0]),
    .pu_row_data(pu_row_data[7:0]),
    .pu_acc_we(pu_acc_we[0]),
    .pu_acc_data(pu_acc_data[ACC_WIDTH-1:0]),
    .rsp_valid(rsp_valid[0]),
    .rsp_data(rsp_data[0]),
    .status(ch_status[0]),
    .bank_open(ch_bank_open[0]),
    .refresh_busy_o(ch_refresh_busy[0]),
    .refresh_bank_o(ch_refresh_bank[0]),
    .bank0_active_data(ch_bank0_data[0]),
    .bank1_active_data(ch_bank1_data[0]),
    .acc_value(ch_acc[0])
  );

  pim_channel #(.REF_PHASE(32)) ch1 (
    .clk(clk),
    .rst_n(rst_n),
    .cmd_valid(cmd_ch1_local),
    .uop_op(decoded_op),
    .uop_subop(decoded_subop),
    .uop_bank_a(decoded_bank_a),
    .uop_row_a(decoded_row_a),
    .uop_imm8(decoded_imm8),
    .pim_busy_status(pu_busy_ch1),
    .pim_error_set(pu_error_set[1]),
    .pu_row_we(pu_row_we[1]),
    .pu_row_bank(pu_row_bank[1]),
    .pu_row_data(pu_row_data[15:8]),
    .pu_acc_we(pu_acc_we[1]),
    .pu_acc_data(pu_acc_data[(2*ACC_WIDTH)-1:ACC_WIDTH]),
    .rsp_valid(rsp_valid[1]),
    .rsp_data(rsp_data[1]),
    .status(ch_status[1]),
    .bank_open(ch_bank_open[1]),
    .refresh_busy_o(ch_refresh_busy[1]),
    .refresh_bank_o(ch_refresh_bank[1]),
    .bank0_active_data(ch_bank0_data[1]),
    .bank1_active_data(ch_bank1_data[1]),
    .acc_value(ch_acc[1])
  );

  // A channel-specific response takes priority. Commands with no read response
  // return a compact acknowledgement containing both status bytes.
  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      rsp_word <= 32'h0000_0000;
    end else if (rsp_valid[0]) begin
      rsp_word <= {8'ha0, ch_status[0], 8'h00, rsp_data[0]};
    end else if (rsp_valid[1]) begin
      rsp_word <= {8'ha1, ch_status[1], 8'h00, rsp_data[1]};
    end else if (cmd_valid) begin
      rsp_word <= {8'h55, ch_status[1], ch_status[0], 8'h00};
    end
  end

  spi_frontend spi (
    .clk(clk),
    .rst_n(rst_n),
    .spi_sclk(ui_in[0]),
    .spi_cs_n(ui_in[1]),
    .spi_mosi(ui_in[2]),
    .spi_miso(spi_miso),
    .cmd_valid(cmd_valid),
    .cmd_word(cmd_word),
    .rsp_word(rsp_word)
  );

  // Debug/status pins: MISO plus open/busy indicators for each channel. The
  // full machine-readable status is available through STATUS commands.
  assign uo_out = {
    ena,
    ch_status[1][4],
    ch_status[1][2],
    ch_status[1][1],
    ch_status[0][4],
    ch_status[0][2],
    ch_status[0][1],
    spi_miso
  };
  assign uio_out = 8'h00;
  assign uio_oe = 8'h00;

  wire _unused = &{1'b0, uio_in, ui_in[7:3], decoded_row_b, decoded_flags[2:1]};
endmodule

`default_nettype wire
