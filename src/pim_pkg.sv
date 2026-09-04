package pim_pkg;
  // The whole controller is intentionally tiny: two independent channels,
  // each with two banks of four 8-bit rows, plus one 18-bit accumulator.
  localparam int NUM_CHANNELS = 2;
  localparam int BANKS_PER_CH = 2;
  localparam int ROWS_PER_BANK = 4;
  localparam int ROW_WIDTH = 8;
  localparam int ACC_WIDTH = 18;
  localparam int REF_INTERVAL = 255;
  localparam int REF_CYCLES = 4;

  // Major opcodes occupy bits 31:28 of the 32-bit SPI command word.
  typedef enum logic [3:0] {
    OP_NOP    = 4'h0,
    OP_ACT    = 4'h1,
    OP_PRE    = 4'h2,
    OP_RD     = 4'h3,
    OP_WR     = 4'h4,
    OP_VOP    = 4'h5,
    OP_REDUCE = 4'h6,
    OP_STREAM = 4'h7,
    OP_ACC    = 4'h8,
    OP_REF    = 4'h9,
    OP_STATUS = 4'ha,
    OP_CONFIG = 4'hb,
    OP_ABORT  = 4'hc
  } pim_opcode_e;

  // Precision selects how an 8-bit row is interpreted by lane operations.
  typedef enum logic [1:0] {
    PREC_INT1 = 2'b00,
    PREC_INT2 = 2'b01,
    PREC_INT4 = 2'b10,
    PREC_INT8 = 2'b11
  } pim_precision_e;

  // Vector ops write an 8-bit row result back into one selected bank.
  typedef enum logic [2:0] {
    VOP_XOR = 3'd0,
    VOP_ADD = 3'd1,
    VOP_AND = 3'd2,
    VOP_OR  = 3'd3,
    VOP_SUB = 3'd4
  } pim_vop_e;

  // Reduction ops write or update the per-channel 18-bit accumulator.
  typedef enum logic [2:0] {
    REDUCE_DOT = 3'd0,
    REDUCE_MAC = 3'd1,
    REDUCE_SUM = 3'd2,
    REDUCE_POPCNT = 3'd3,
    REDUCE_XNORDOT = 3'd4
  } pim_reduce_e;

  // Decoded command fields. These names track the public ISA table in README.md.
  typedef struct packed {
    logic [3:0] op;
    logic       ch;
    logic [2:0] subop;
    logic [1:0] precision;
    logic       bank_a;
    logic       bank_b;
    logic [1:0] row_a;
    logic [1:0] row_b;
    logic [2:0] flags;
    logic [7:0] imm8;
  } pim_uop_t;
endpackage
