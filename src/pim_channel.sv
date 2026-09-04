`default_nettype none

module pim_channel #(
  parameter int REF_PHASE = 0
) (
  input  logic             clk,
  input  logic             rst_n,
  input  logic             cmd_valid,
  input  pim_pkg::pim_uop_t uop,
  output logic             rsp_valid,
  output logic [7:0]       rsp_data,
  output logic [7:0]       status
);
  import pim_pkg::*;
  localparam logic [7:0] REF_RELOAD_DEFAULT = REF_INTERVAL[7:0] - 8'd1;

  // Minimal row storage: two banks, four addressable rows per bank, 8 bits/row.
  logic [ROW_WIDTH-1:0] rows [BANKS_PER_CH-1:0][ROWS_PER_BANK-1:0];
  logic open [BANKS_PER_CH-1:0];
  logic [1:0] active_row [BANKS_PER_CH-1:0];

  // Automatic refresh state. A zero counter creates a pending refresh; refresh
  // starts when no PIM operation is busy. Forced REF bypasses refresh_enable.
  logic [7:0] refresh_ctr;
  logic [7:0] refresh_reload;
  logic       refresh_enable;
  logic [2:0] refresh_busy_ctr;
  logic       refresh_bank;
  logic       refresh_pending;
  logic       refresh_overdue;
  logic       sticky_error;

  // PIM operation state. VOPs are delayed writes; DOT/MAC/STREAM use the
  // accumulator and lane-serial dot-product state below.
  logic [ACC_WIDTH-1:0] acc;
  logic [7:0] pim_busy_ctr;
  logic [3:0] active_op;
  logic [1:0] active_precision;
  logic       active_dest_bank;
  logic [ROW_WIDTH-1:0] vop_result;
  logic [ROW_WIDTH-1:0] active_operand_a;
  logic [ROW_WIDTH-1:0] active_operand_b;

  // One-entry command queue. It accepts one command while this channel's PIM
  // datapath is busy; a second queued command sets sticky_error.
  pim_uop_t pending_uop;
  logic pending_valid;
  pim_uop_t exec_uop;
  logic exec_cmd_valid;
  logic [2:0] dot_lane;

  // STREAM walks consecutive row pairs, feeding each pair into the same DOT/MAC
  // accumulator datapath as a standalone REDUCE operation.
  logic stream_active;
  logic [1:0] stream_precision;
  logic stream_bank_a;
  logic stream_bank_b;
  logic [1:0] stream_row_a;
  logic [1:0] stream_row_b;
  logic [2:0] stream_remaining;
  logic       refresh_busy;
  logic       pim_busy;
  logic       target_open;
  logic       target_refreshing;
  logic [1:0] target_row;
  logic       row_invalid;
  logic       both_operands_ready;
  logic       either_operand_refreshing;
  logic [ROW_WIDTH-1:0] operand_a;
  logic [ROW_WIDTH-1:0] operand_b;
  logic last_dot_lane;

  assign refresh_busy = (refresh_busy_ctr != 3'd0);
  assign pim_busy = (pim_busy_ctr != 8'd0);
  assign exec_cmd_valid = pending_valid || cmd_valid;
  assign exec_uop = pending_valid ? pending_uop : uop;
  assign target_open = open[exec_uop.bank_a];
  assign target_row = active_row[exec_uop.bank_a];
  assign row_invalid = 1'b0;
  assign target_refreshing = refresh_busy && (refresh_bank == exec_uop.bank_a);
  assign both_operands_ready = open[exec_uop.bank_a] && open[exec_uop.bank_b];
  assign either_operand_refreshing =
    refresh_busy && ((refresh_bank == exec_uop.bank_a) || (refresh_bank == exec_uop.bank_b));
  assign operand_a = rows[exec_uop.bank_a][active_row[exec_uop.bank_a]];
  assign operand_b = rows[exec_uop.bank_b][active_row[exec_uop.bank_b]];
  assign last_dot_lane = (dot_lane == dot_last_lane(active_precision));

  // Some decoded fields are reserved for future ISA growth. Keep them visibly
  // consumed so lint warnings do not hide real unused signals.
  wire _unused_stage2_uop = &{
    1'b0,
    exec_uop.ch,
    exec_uop.subop[2],
    exec_uop.flags[2:1]
  };

  // Status bits match README.md/docs/isa.md bit order.
  assign status = {
    sticky_error,
    refresh_overdue,
    refresh_pending,
    refresh_busy,
    pim_busy,
    open[1],
    open[0],
    pending_valid
  };

  integer bank_i;
  integer row_i;

  function automatic logic signed [8:0] sign_extend_lane (
    input logic [7:0] value,
    input logic [1:0] precision,
    input logic [2:0] lane
  );
    logic signed [1:0] lane2;
    logic signed [3:0] lane4;
    logic signed [7:0] lane8;
    begin
      // INT2 has four 2-bit lanes, INT4 has two 4-bit lanes, and INT8 has one
      // whole-row lane. INT1 reductions handle unsigned bits separately.
      lane2 = value[lane * 2 +: 2];
      lane4 = value[lane * 4 +: 4];
      lane8 = value;
      unique case (precision)
        PREC_INT2: sign_extend_lane = {{7{lane2[1]}}, lane2};
        PREC_INT4: sign_extend_lane = {{5{lane4[3]}}, lane4};
        default:   sign_extend_lane = {lane8[7], lane8};
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
        PREC_INT8: result = a + b;
        default:   result = 8'h00;
      endcase
      lane_add_wrap = result;
    end
  endfunction

  function automatic logic [7:0] lane_sub_wrap (
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
            result[lane * 2 +: 2] = a[lane * 2 +: 2] - b[lane * 2 +: 2];
          end
        end
        PREC_INT4: begin
          for (lane = 0; lane < 2; lane = lane + 1) begin
            result[lane * 4 +: 4] = a[lane * 4 +: 4] - b[lane * 4 +: 4];
          end
        end
        PREC_INT8: result = a - b;
        default:   result = 8'h00;
      endcase
      lane_sub_wrap = result;
    end
  endfunction

  function automatic logic signed [ACC_WIDTH-1:0] acc_extend_lane (
    input logic [7:0] value,
    input logic [1:0] precision,
    input logic [2:0] lane
  );
    logic signed [8:0] lane_value;
    begin
      lane_value = sign_extend_lane(value, precision, lane);
      acc_extend_lane = {{(ACC_WIDTH-9){lane_value[8]}}, lane_value};
    end
  endfunction

  function automatic logic signed [ACC_WIDTH-1:0] lane_sum (
    input logic [7:0] value,
    input logic [1:0] precision
  );
    logic signed [ACC_WIDTH-1:0] total;
    int lane;
    begin
      total = '0;
      if (precision == PREC_INT1) begin
        for (lane = 0; lane < 8; lane = lane + 1) begin
          total = total + {{(ACC_WIDTH-1){1'b0}}, value[lane]};
        end
      end else if (precision == PREC_INT2) begin
        total = acc_extend_lane(value, precision, 3'd0);
        total = total + acc_extend_lane(value, precision, 3'd1);
        total = total + acc_extend_lane(value, precision, 3'd2);
        total = total + acc_extend_lane(value, precision, 3'd3);
      end else if (precision == PREC_INT4) begin
        total = acc_extend_lane(value, precision, 3'd0);
        total = total + acc_extend_lane(value, precision, 3'd1);
      end else begin
        total = acc_extend_lane(value, precision, 3'd0);
      end
      lane_sum = total;
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

  function automatic logic [ACC_WIDTH-1:0] xnordot8 (
    input logic [7:0] a,
    input logic [7:0] b
  );
    logic [3:0] match_count;
    int bit_i;
    begin
      match_count = 4'd0;
      for (bit_i = 0; bit_i < 8; bit_i = bit_i + 1) begin
        match_count = match_count + {3'd0, ~(a[bit_i] ^ b[bit_i])};
      end
      xnordot8 = ({{(ACC_WIDTH-4){1'b0}}, match_count} << 1) -
        {{(ACC_WIDTH-4){1'b0}}, 4'd8};
    end
  endfunction

  function automatic logic signed [ACC_WIDTH-1:0] dot_lane_term (
    input logic [1:0] precision,
    input logic [7:0] a,
    input logic [7:0] b,
    input logic [2:0] lane
  );
    logic signed [8:0] lane_a;
    logic signed [8:0] lane_b;
    begin
      if (precision == PREC_INT1) begin
        // INT1 DOT is a bitwise AND popcount over all eight bit lanes.
        dot_lane_term = popcount8(a & b);
      end else begin
        // Wider precisions add one signed lane product per busy cycle.
        lane_a = sign_extend_lane(a, precision, lane);
        lane_b = sign_extend_lane(b, precision, lane);
        dot_lane_term = lane_a * lane_b;
      end
    end
  endfunction

  function automatic logic valid_stream_count (
    input logic [1:0] start_a,
    input logic [1:0] start_b,
    input logic [2:0] count
  );
    logic [2:0] end_a;
    logic [2:0] end_b;
    begin
      end_a = {1'b0, start_a} + count;
      end_b = {1'b0, start_b} + count;
      valid_stream_count = (count != 3'd0) && (end_a <= 3'd4) && (end_b <= 3'd4);
    end
  endfunction

  task automatic start_stream_reduce (
    input logic [1:0] precision,
    input logic bank_a,
    input logic bank_b,
    input logic [1:0] row_a,
    input logic [1:0] row_b
  );
    logic [7:0] stream_operand_a;
    logic [7:0] stream_operand_b;
    begin
      // Capture row data before updating active_row so each streamed row pair
      // is reduced exactly once.
      stream_operand_a = rows[bank_a][row_a];
      stream_operand_b = rows[bank_b][row_b];
      open[bank_a] <= 1'b1;
      open[bank_b] <= 1'b1;
      active_row[bank_a] <= row_a;
      active_row[bank_b] <= row_b;
      active_op <= OP_REDUCE;
      active_precision <= precision;
      active_dest_bank <= 1'b0;
      vop_result <= '0;
      active_operand_a <= stream_operand_a;
      active_operand_b <= stream_operand_b;
      dot_lane <= 3'd0;
      pim_busy_ctr <= dot_latency(precision);
    end
  endtask

  function automatic logic [2:0] dot_last_lane (
    input logic [1:0] precision
  );
    begin
      unique case (precision)
        PREC_INT1: dot_last_lane = 3'd7;
        PREC_INT2: dot_last_lane = 3'd3;
        PREC_INT4: dot_last_lane = 3'd1;
        default:   dot_last_lane = 3'd0;
      endcase
    end
  endfunction

  function automatic logic [3:0] op_latency (
    input logic [3:0] op,
    input logic [1:0] precision
  );
    begin
      if (op == OP_VOP) begin
        unique case (precision)
          PREC_INT1: op_latency = 4'd8;
          PREC_INT2: op_latency = 4'd4;
          PREC_INT4: op_latency = 4'd2;
          default:   op_latency = 4'd1;
        endcase
      end else begin
        op_latency = 4'd15;
      end
    end
  endfunction

  function automatic logic [7:0] dot_latency (
    input logic [1:0] precision
  );
    begin
      // Lane-serial compromise: one cycle for INT1/INT8, two cycles for INT4,
      // and four cycles for INT2.
      unique case (precision)
        PREC_INT2: dot_latency = 8'd4;
        PREC_INT4: dot_latency = 8'd2;
        default:   dot_latency = 8'd1;
      endcase
    end
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      for (bank_i = 0; bank_i < BANKS_PER_CH; bank_i = bank_i + 1) begin
        open[bank_i] <= 1'b0;
        active_row[bank_i] <= 2'd0;
        for (row_i = 0; row_i < ROWS_PER_BANK; row_i = row_i + 1) begin
          rows[bank_i][row_i] <= '0;
        end
      end
      refresh_ctr <= REF_PHASE[7:0];
      refresh_reload <= REF_RELOAD_DEFAULT;
      refresh_enable <= 1'b1;
      refresh_busy_ctr <= 3'd0;
      refresh_bank <= 1'b0;
      refresh_pending <= 1'b0;
      refresh_overdue <= 1'b0;
      sticky_error <= 1'b0;
      acc <= '0;
      pim_busy_ctr <= 8'd0;
      active_op <= OP_NOP;
      active_precision <= PREC_INT1;
      active_dest_bank <= 1'b0;
      vop_result <= '0;
      active_operand_a <= '0;
      active_operand_b <= '0;
      pending_uop <= '0;
      pending_valid <= 1'b0;
      dot_lane <= 3'd0;
      stream_active <= 1'b0;
      stream_precision <= PREC_INT1;
      stream_bank_a <= 1'b0;
      stream_bank_b <= 1'b0;
      stream_row_a <= 2'd0;
      stream_row_b <= 2'd0;
      stream_remaining <= 3'd0;
      rsp_valid <= 1'b0;
      rsp_data <= 8'h00;
    end else begin
      rsp_valid <= 1'b0;

      if (refresh_enable) begin
        // Automatic refresh scheduling is decoupled from forced REF commands.
        if (refresh_ctr == 8'd0) begin
          refresh_ctr <= refresh_reload;
          if (refresh_busy || refresh_pending) begin
            refresh_overdue <= 1'b1;
          end else begin
            refresh_pending <= 1'b1;
          end
        end else begin
          refresh_ctr <= refresh_ctr - 8'd1;
        end
      end

      if (refresh_busy) begin
        refresh_busy_ctr <= refresh_busy_ctr - 3'd1;
      end else if (refresh_pending && !pim_busy) begin
        // Defer autonomous refresh until the atomic PIM datapath is idle.
        refresh_pending <= 1'b0;
        refresh_busy_ctr <= REF_CYCLES[2:0];
        refresh_bank <= ~refresh_bank;
      end

      if (pim_busy) begin
        if (cmd_valid) begin
          if (pending_valid) begin
            sticky_error <= 1'b1;
          end else begin
            pending_uop <= uop;
            pending_valid <= 1'b1;
          end
        end
        pim_busy_ctr <= pim_busy_ctr - 8'd1;
        if (active_op == OP_REDUCE) begin
          // DOT/MAC accumulates one lane term each cycle. DOT cleared acc when
          // it started; MAC leaves the prior accumulator value intact.
          acc <= acc + dot_lane_term(active_precision, active_operand_a, active_operand_b, dot_lane);
          if (last_dot_lane || (pim_busy_ctr == 8'd1)) begin
            dot_lane <= 3'd0;
          end else begin
            dot_lane <= dot_lane + 3'd1;
          end
        end
        if (pim_busy_ctr == 8'd1) begin
          // Complete the atomic operation. VOP commits its delayed row write;
          // STREAM either advances to the next row pair or terminates.
          unique case (active_op)
            OP_VOP: begin
              rows[active_dest_bank][active_row[active_dest_bank]] <= vop_result;
            end
            OP_REDUCE: begin
              if (stream_active) begin
                if (stream_remaining == 3'd0) begin
                  stream_active <= 1'b0;
                end else begin
                  start_stream_reduce(
                    stream_precision,
                    stream_bank_a,
                    stream_bank_b,
                    stream_row_a,
                    stream_row_b
                  );
                  stream_row_a <= stream_row_a + 2'd1;
                  stream_row_b <= stream_row_b + 2'd1;
                  stream_remaining <= stream_remaining - 3'd1;
                end
              end
            end
            default: begin
              sticky_error <= 1'b1;
            end
          endcase
        end
      end else if (exec_cmd_valid) begin
        if (pending_valid) begin
          // Drain the queued command and optionally capture a new command in
          // the same cycle.
          pending_valid <= cmd_valid;
          pending_uop <= uop;
        end

        unique case (exec_uop.op)
          OP_NOP: begin
            rsp_valid <= 1'b1;
            rsp_data <= 8'h00;
          end
          OP_ACT: begin
            if (target_refreshing || row_invalid) begin
              sticky_error <= 1'b1;
            end else begin
              open[exec_uop.bank_a] <= 1'b1;
              active_row[exec_uop.bank_a] <= exec_uop.row_a;
            end
          end
          OP_PRE: begin
            if (target_refreshing) begin
              sticky_error <= 1'b1;
            end else begin
              open[exec_uop.bank_a] <= 1'b0;
            end
          end
          OP_WR: begin
            if (!target_open || target_refreshing) begin
              sticky_error <= 1'b1;
            end else begin
              rows[exec_uop.bank_a][target_row] <= exec_uop.imm8;
            end
          end
          OP_RD: begin
            rsp_valid <= 1'b1;
            if (!target_open || target_refreshing) begin
              rsp_data <= 8'h00;
              sticky_error <= 1'b1;
            end else begin
              rsp_data <= rows[exec_uop.bank_a][target_row];
            end
          end
          OP_REF: begin
            if (refresh_busy) begin
              refresh_overdue <= 1'b1;
            end else begin
              refresh_busy_ctr <= REF_CYCLES[2:0];
              refresh_bank <= exec_uop.bank_a;
              refresh_pending <= 1'b0;
            end
          end
          OP_VOP: begin
            // VOP operands must both be open and not under refresh. The result
            // is captured now and written back when pim_busy_ctr expires.
            if (!both_operands_ready || either_operand_refreshing) begin
              sticky_error <= 1'b1;
            end else if (
              (exec_uop.subop != VOP_XOR) &&
              (exec_uop.subop != VOP_ADD) &&
              (exec_uop.subop != VOP_AND) &&
              (exec_uop.subop != VOP_OR) &&
              (exec_uop.subop != VOP_SUB)
            ) begin
              sticky_error <= 1'b1;
            end else if (
              ((exec_uop.subop == VOP_ADD) || (exec_uop.subop == VOP_SUB)) &&
              (exec_uop.precision == PREC_INT1)
            ) begin
              sticky_error <= 1'b1;
            end else begin
              active_op <= OP_VOP;
              active_precision <= exec_uop.precision;
              active_dest_bank <= exec_uop.flags[0];
              unique case (exec_uop.subop)
                VOP_XOR: vop_result <= operand_a ^ operand_b;
                VOP_AND: vop_result <= operand_a & operand_b;
                VOP_OR:  vop_result <= operand_a | operand_b;
                VOP_ADD: vop_result <= lane_add_wrap(operand_a, operand_b, exec_uop.precision);
                default: vop_result <= lane_sub_wrap(operand_a, operand_b, exec_uop.precision);
              endcase
              pim_busy_ctr <= {4'd0, op_latency(exec_uop.op, exec_uop.precision)};
            end
          end
          OP_REDUCE: begin
            // SUM/POPCNT/XNORDOT complete immediately. DOT/MAC enter the
            // lane-serial busy path above.
            if (!both_operands_ready || either_operand_refreshing) begin
              sticky_error <= 1'b1;
            end else if (
              (exec_uop.subop != REDUCE_DOT) &&
              (exec_uop.subop != REDUCE_MAC) &&
              (exec_uop.subop != REDUCE_SUM) &&
              (exec_uop.subop != REDUCE_POPCNT) &&
              (exec_uop.subop != REDUCE_XNORDOT)
            ) begin
              sticky_error <= 1'b1;
            end else if (
              ((exec_uop.subop == REDUCE_POPCNT) || (exec_uop.subop == REDUCE_XNORDOT)) &&
              (exec_uop.precision != PREC_INT1)
            ) begin
              sticky_error <= 1'b1;
            end else if (exec_uop.subop == REDUCE_SUM) begin
              acc <= lane_sum(operand_a, exec_uop.precision);
            end else if (exec_uop.subop == REDUCE_POPCNT) begin
              acc <= popcount8(operand_a);
            end else if (exec_uop.subop == REDUCE_XNORDOT) begin
              acc <= xnordot8(operand_a, operand_b);
            end else begin
              active_op <= OP_REDUCE;
              active_precision <= exec_uop.precision;
              active_dest_bank <= 1'b0;
              vop_result <= '0;
              active_operand_a <= operand_a;
              active_operand_b <= operand_b;
              dot_lane <= 3'd0;
              if (exec_uop.subop == REDUCE_DOT) begin
                acc <= '0;
              end
              pim_busy_ctr <= dot_latency(exec_uop.precision);
            end
          end
          OP_STREAM: begin
            // STREAM opens and reduces consecutive row pairs. It is blocked
            // while refresh is pending/busy to avoid mid-stream row conflicts.
            if (refresh_busy || refresh_pending) begin
              sticky_error <= 1'b1;
            end else if ((exec_uop.subop != REDUCE_DOT) && (exec_uop.subop != REDUCE_MAC)) begin
              sticky_error <= 1'b1;
            end else if (!valid_stream_count(exec_uop.row_a, exec_uop.row_b, exec_uop.imm8[2:0])) begin
              sticky_error <= 1'b1;
            end else begin
              stream_active <= 1'b1;
              stream_precision <= exec_uop.precision;
              stream_bank_a <= exec_uop.bank_a;
              stream_bank_b <= exec_uop.bank_b;
              stream_row_a <= exec_uop.row_a + 2'd1;
              stream_row_b <= exec_uop.row_b + 2'd1;
              stream_remaining <= exec_uop.imm8[2:0] - 3'd1;
              if (exec_uop.subop == REDUCE_DOT) begin
                acc <= '0;
              end
              start_stream_reduce(
                exec_uop.precision,
                exec_uop.bank_a,
                exec_uop.bank_b,
                exec_uop.row_a,
                exec_uop.row_b
              );
            end
          end
          OP_ACC: begin
            rsp_valid <= 1'b1;
            unique case (exec_uop.subop[1:0])
              2'd0: rsp_data <= acc[7:0];
              2'd1: rsp_data <= acc[15:8];
              default: rsp_data <= {{(8-(ACC_WIDTH-16)){1'b0}}, acc[ACC_WIDTH-1:16]};
            endcase
            if (exec_uop.subop == 3'd4) begin
              acc <= '0;
            end
          end
          OP_STATUS: begin
            rsp_valid <= 1'b1;
            rsp_data <= status;
          end
          OP_CONFIG: begin
            // CONFIG is intentionally narrow: refresh reload read/write plus
            // automatic-refresh enable read/write.
            unique case (exec_uop.subop)
              3'd0: begin
                refresh_reload <= exec_uop.imm8;
                refresh_ctr <= exec_uop.imm8;
              end
              3'd1: begin
                rsp_valid <= 1'b1;
                rsp_data <= refresh_reload;
              end
              3'd2: begin
                refresh_enable <= exec_uop.imm8[0];
                refresh_ctr <= refresh_reload;
                if (!exec_uop.imm8[0]) begin
                  refresh_pending <= 1'b0;
                  refresh_overdue <= 1'b0;
                end
              end
              3'd3: begin
                rsp_valid <= 1'b1;
                rsp_data <= {7'd0, refresh_enable};
              end
              default: begin
                sticky_error <= 1'b1;
              end
            endcase
          end
          OP_ABORT: begin
            refresh_pending <= 1'b0;
            refresh_busy_ctr <= 3'd0;
            refresh_overdue <= 1'b0;
            sticky_error <= 1'b0;
            acc <= '0;
            pim_busy_ctr <= 8'd0;
            active_op <= OP_NOP;
            pending_valid <= 1'b0;
            stream_active <= 1'b0;
            stream_remaining <= 3'd0;
          end
          default: begin
            sticky_error <= 1'b1;
            rsp_valid <= 1'b1;
            rsp_data <= 8'hff;
          end
        endcase
      end
    end
  end
endmodule

`default_nettype wire
