`default_nettype none

module command_decoder (
  input  logic [31:0]          cmd_word,
  output pim_pkg::pim_uop_t    uop
);
  import pim_pkg::*;

  always_comb begin
    // Fixed-width SPI frames decode directly into the internal micro-op.
    uop.op        = cmd_word[31:28];
    uop.ch        = cmd_word[27];
    uop.subop     = cmd_word[26:24];
    uop.precision = cmd_word[23:22];
    uop.bank_a    = cmd_word[21];
    uop.bank_b    = cmd_word[20];
    uop.row_a     = cmd_word[19:18];
    uop.row_b     = cmd_word[17:16];
    uop.flags     = cmd_word[10:8];
    uop.imm8      = cmd_word[7:0];
  end

  // Bits 15:11 are reserved in the ISA. Fold them into a dummy reduction so
  // lint sees them as intentionally consumed.
  wire _unused_reserved = &{1'b0, cmd_word[15:11]};
endmodule

`default_nettype wire
