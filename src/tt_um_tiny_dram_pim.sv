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

  // Channel refresh phases are staggered so the two banks do not request
  // autonomous refresh on the same core cycle after reset.
  pim_channel #(.REF_PHASE(0)) ch0 (
    .clk(clk),
    .rst_n(rst_n),
    .cmd_valid(cmd_ch0),
    .uop_op(decoded_op),
    .uop_ch(decoded_ch),
    .uop_subop(decoded_subop),
    .uop_precision(decoded_precision),
    .uop_bank_a(decoded_bank_a),
    .uop_bank_b(decoded_bank_b),
    .uop_row_a(decoded_row_a),
    .uop_row_b(decoded_row_b),
    .uop_flags(decoded_flags),
    .uop_imm8(decoded_imm8),
    .rsp_valid(rsp_valid[0]),
    .rsp_data(rsp_data[0]),
    .status(ch_status[0])
  );

  pim_channel #(.REF_PHASE(32)) ch1 (
    .clk(clk),
    .rst_n(rst_n),
    .cmd_valid(cmd_ch1),
    .uop_op(decoded_op),
    .uop_ch(decoded_ch),
    .uop_subop(decoded_subop),
    .uop_precision(decoded_precision),
    .uop_bank_a(decoded_bank_a),
    .uop_bank_b(decoded_bank_b),
    .uop_row_a(decoded_row_a),
    .uop_row_b(decoded_row_b),
    .uop_flags(decoded_flags),
    .uop_imm8(decoded_imm8),
    .rsp_valid(rsp_valid[1]),
    .rsp_data(rsp_data[1]),
    .status(ch_status[1])
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

  wire _unused = &{1'b0, uio_in, ui_in[7:3]};
endmodule

`default_nettype wire
