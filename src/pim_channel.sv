`default_nettype none

module pim_channel #(
  parameter int REF_PHASE = 0
) (
  input  logic             clk,
  input  logic             rst_n,
  input  logic             cmd_valid,
  input  logic [3:0]       uop_op,
  input  logic [2:0]       uop_subop,
  input  logic             uop_bank_a,
  input  logic [1:0]       uop_row_a,
  input  logic [7:0]       uop_imm8,
  input  logic             pim_busy_status,
  input  logic             pim_error_set,
  input  logic             pu_row_we,
  input  logic             pu_row_bank,
  input  logic [7:0]       pu_row_data,
  input  logic             pu_acc_we,
  input  logic [7:0]       pu_acc_data,
  output logic             rsp_valid,
  output logic [7:0]       rsp_data,
  output logic [7:0]       status,
  output logic [1:0]       bank_open,
  output logic             refresh_busy_o,
  output logic             refresh_bank_o,
  output logic [7:0]       bank0_active_data,
  output logic [7:0]       bank1_active_data,
  output logic [7:0]       acc_value
);
  localparam int BANKS_PER_CH = 2;
  localparam int ROWS_PER_BANK = 2;
  localparam int ROW_WIDTH = 8;
  localparam int ACC_WIDTH = 8;
  localparam int REF_INTERVAL = 255;
  localparam int REF_CYCLES = 4;

  localparam logic [3:0] OP_NOP    = 4'h0;
  localparam logic [3:0] OP_ACT    = 4'h1;
  localparam logic [3:0] OP_PRE    = 4'h2;
  localparam logic [3:0] OP_RD     = 4'h3;
  localparam logic [3:0] OP_WR     = 4'h4;
  localparam logic [3:0] OP_VOP    = 4'h5;
  localparam logic [3:0] OP_REDUCE = 4'h6;
  localparam logic [3:0] OP_ACC    = 4'h8;
  localparam logic [3:0] OP_REF    = 4'h9;
  localparam logic [3:0] OP_STATUS = 4'ha;
  localparam logic [3:0] OP_CONFIG = 4'hb;
  localparam logic [3:0] OP_ABORT  = 4'hc;

  logic [ROW_WIDTH-1:0] rows [BANKS_PER_CH-1:0][ROWS_PER_BANK-1:0];
  logic open [BANKS_PER_CH-1:0];
  logic active_row [BANKS_PER_CH-1:0];

  logic [7:0] refresh_ctr;
  logic       refresh_enable;
  logic [2:0] refresh_busy_ctr;
  logic       refresh_bank;
  logic       refresh_pending;
  logic       refresh_overdue;
  logic       sticky_error;
  logic [ACC_WIDTH-1:0] acc;

  logic refresh_busy;
  logic target_open;
  logic target_refreshing;
  logic target_row;
  logic row_invalid;

  assign refresh_busy = (refresh_busy_ctr != 3'd0);
  assign target_open = open[uop_bank_a];
  assign target_row = active_row[uop_bank_a];
  assign row_invalid = uop_row_a[1];
  assign target_refreshing = refresh_busy && (refresh_bank == uop_bank_a);

  assign bank_open = {open[1], open[0]};
  assign refresh_busy_o = refresh_busy;
  assign refresh_bank_o = refresh_bank;
  assign bank0_active_data = rows[0][active_row[0]];
  assign bank1_active_data = rows[1][active_row[1]];
  assign acc_value = acc;

  assign status = {
    sticky_error,
    refresh_overdue,
    refresh_pending,
    refresh_busy,
    pim_busy_status,
    open[1],
    open[0],
    1'b0
  };

  integer bank_i;
  integer row_i;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      for (bank_i = 0; bank_i < BANKS_PER_CH; bank_i = bank_i + 1) begin
        open[bank_i] <= 1'b0;
        active_row[bank_i] <= 1'b0;
        for (row_i = 0; row_i < ROWS_PER_BANK; row_i = row_i + 1) begin
          rows[bank_i][row_i] <= '0;
        end
      end
      refresh_ctr <= REF_PHASE[7:0];
      refresh_enable <= 1'b1;
      refresh_busy_ctr <= 3'd0;
      refresh_bank <= 1'b0;
      refresh_pending <= 1'b0;
      refresh_overdue <= 1'b0;
      sticky_error <= 1'b0;
      acc <= '0;
      rsp_valid <= 1'b0;
      rsp_data <= 8'h00;
    end else begin
      rsp_valid <= 1'b0;

      if (refresh_enable) begin
        if (refresh_ctr == 8'd0) begin
          refresh_ctr <= REF_INTERVAL[7:0] - 8'd1;
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
      end else if (refresh_pending && !pim_busy_status) begin
        refresh_pending <= 1'b0;
        refresh_busy_ctr <= REF_CYCLES[2:0];
        refresh_bank <= ~refresh_bank;
      end

      if (pu_row_we) begin
        rows[pu_row_bank][active_row[pu_row_bank]] <= pu_row_data;
      end
      if (pu_acc_we) begin
        acc <= pu_acc_data;
      end
      if (pim_error_set) begin
        sticky_error <= 1'b1;
      end

      if (cmd_valid && pim_busy_status && (uop_op != OP_ABORT)) begin
        sticky_error <= 1'b1;
      end else if (cmd_valid) begin
        unique case (uop_op)
          OP_NOP: begin
            rsp_valid <= 1'b1;
            rsp_data <= 8'h00;
          end
          OP_ACT: begin
            if (target_refreshing || row_invalid) begin
              sticky_error <= 1'b1;
            end else begin
              open[uop_bank_a] <= 1'b1;
              active_row[uop_bank_a] <= uop_row_a[0];
            end
          end
          OP_PRE: begin
            if (target_refreshing) begin
              sticky_error <= 1'b1;
            end else begin
              open[uop_bank_a] <= 1'b0;
            end
          end
          OP_WR: begin
            if (!target_open || target_refreshing) begin
              sticky_error <= 1'b1;
            end else begin
              rows[uop_bank_a][target_row] <= uop_imm8;
            end
          end
          OP_RD: begin
            rsp_valid <= 1'b1;
            if (!target_open || target_refreshing) begin
              rsp_data <= 8'h00;
              sticky_error <= 1'b1;
            end else begin
              rsp_data <= rows[uop_bank_a][target_row];
            end
          end
          OP_REF: begin
            if (refresh_busy) begin
              refresh_overdue <= 1'b1;
            end else begin
              refresh_busy_ctr <= REF_CYCLES[2:0];
              refresh_bank <= uop_bank_a;
              refresh_pending <= 1'b0;
            end
          end
          OP_VOP, OP_REDUCE: begin
            sticky_error <= 1'b1;
          end
          OP_ACC: begin
            rsp_valid <= 1'b1;
            unique case (uop_subop[1:0])
              2'd0: rsp_data <= acc[7:0];
              2'd1: rsp_data <= 8'h00;
              default: rsp_data <= 8'h00;
            endcase
            if (uop_subop == 3'd4) begin
              acc <= '0;
            end
          end
          OP_STATUS: begin
            rsp_valid <= 1'b1;
            rsp_data <= status;
          end
          OP_CONFIG: begin
            unique case (uop_subop)
              3'd2: begin
                refresh_enable <= uop_imm8[0];
                refresh_ctr <= REF_INTERVAL[7:0] - 8'd1;
                if (!uop_imm8[0]) begin
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
