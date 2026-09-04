`default_nettype none

module spi_frontend (
  input  logic        clk,
  input  logic        rst_n,
  input  logic        spi_sclk,
  input  logic        spi_cs_n,
  input  logic        spi_mosi,
  output logic        spi_miso,
  output logic        cmd_valid,
  output logic [31:0] cmd_word,
  input  logic [31:0] rsp_word
);
  logic [2:0] sclk_sync;
  logic [2:0] cs_sync;
  logic [1:0] mosi_sync;
  logic [30:0] rx_shift;
  logic [31:0] tx_shift;
  logic [5:0] bit_count;
  logic cs_active_d;

  // SPI pins are asynchronous to clk, so sample them through small sync chains
  // and edge-detect in the core clock domain.
  wire sclk_rise = (sclk_sync[2:1] == 2'b01);
  wire sclk_fall = (sclk_sync[2:1] == 2'b10);
  wire cs_active = ~cs_sync[2];
  wire cs_start = cs_active & ~cs_active_d;

  // Responses are preloaded on CS assertion and shifted MSB first.
  assign spi_miso = cs_active ? tx_shift[31] : 1'b0;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      sclk_sync  <= 3'b000;
      cs_sync    <= 3'b111;
      mosi_sync  <= 2'b00;
      rx_shift   <= 31'h0000_0000;
      tx_shift   <= 32'h0000_0000;
      bit_count  <= 6'd0;
      cmd_valid  <= 1'b0;
      cmd_word   <= 32'h0000_0000;
      cs_active_d <= 1'b0;
    end else begin
      sclk_sync <= {sclk_sync[1:0], spi_sclk};
      cs_sync   <= {cs_sync[1:0], spi_cs_n};
      mosi_sync <= {mosi_sync[0], spi_mosi};
      cmd_valid <= 1'b0;
      cs_active_d <= cs_active;

      if (cs_start) begin
        // A new SPI frame captures the current response word. The response for
        // this command will be visible on the following frame.
        rx_shift  <= 31'h0000_0000;
        tx_shift  <= rsp_word;
        bit_count <= 6'd0;
      end else if (!cs_active) begin
        bit_count <= 6'd0;
      end else begin
        if (sclk_rise) begin
          // Commands are sampled MSB first. cmd_valid pulses for one clk when
          // the 32nd command bit arrives.
          rx_shift <= {rx_shift[29:0], mosi_sync[1]};
          if (bit_count == 6'd31) begin
            cmd_valid <= 1'b1;
            cmd_word  <= {rx_shift, mosi_sync[1]};
            bit_count <= 6'd0;
          end else begin
            bit_count <= bit_count + 6'd1;
          end
        end
        if (sclk_fall) begin
          // Shift MISO on falling SCLK so the next bit is stable before the
          // external master samples on the next rising edge.
          tx_shift <= {tx_shift[30:0], 1'b0};
        end
      end
    end
  end
endmodule

`default_nettype wire
