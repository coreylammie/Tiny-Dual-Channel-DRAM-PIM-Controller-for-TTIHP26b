`default_nettype none

module command_decoder (
  input  logic [31:0] cmd_word,
  output logic [3:0]  op,
  output logic        ch,
  output logic [2:0]  subop,
  output logic [1:0]  precision,
  output logic        bank_a,
  output logic        bank_b,
  output logic [1:0]  row_a,
  output logic [1:0]  row_b,
  output logic [2:0]  flags,
  output logic [7:0]  imm8
);
  always_comb begin
    // Fixed-width SPI frames decode directly into the internal micro-op.
    op        = cmd_word[31:28];
    ch        = cmd_word[27];
    subop     = cmd_word[26:24];
    precision = cmd_word[23:22];
    bank_a    = cmd_word[21];
    bank_b    = cmd_word[20];
    row_a     = cmd_word[19:18];
    row_b     = cmd_word[17:16];
    flags     = cmd_word[10:8];
    imm8      = cmd_word[7:0];
  end

  // Bits 15:11 are reserved in the ISA. Fold them into a dummy reduction so
  // lint sees them as intentionally consumed.
  wire _unused_reserved = &{1'b0, cmd_word[15:11]};
endmodule

`default_nettype wire
