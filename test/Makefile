# Makefile for TinyTapeout/cocotb RTL and gate-level tests.

SIM ?= icarus
FST ?= -fst
TOPLEVEL_LANG ?= verilog
SRC_DIR = $(CURDIR)/../src
PROJECT_SOURCES = command_decoder.sv spi_frontend.sv pim_channel.sv tt_um_tiny_dram_pim.sv

export PYTHONPATH := $(CURDIR)/..:$(PYTHONPATH)

ifneq ($(GATES),yes)

SIM_BUILD = sim_build/rtl
VERILOG_SOURCES += $(addprefix $(SRC_DIR)/,$(PROJECT_SOURCES))

else

SIM_BUILD = sim_build/gl
COMPILE_ARGS += -DGL_TEST
COMPILE_ARGS += -DFUNCTIONAL
COMPILE_ARGS += -DSIM
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13g2/libs.ref/sg13g2_io/verilog/sg13g2_io.v
VERILOG_SOURCES += $(PDK_ROOT)/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog/sg13g2_stdcell.v
VERILOG_SOURCES += $(CURDIR)/gate_level_netlist.v

endif

COMPILE_ARGS += -g2012
COMPILE_ARGS += -I$(SRC_DIR)
VERILOG_SOURCES += $(CURDIR)/tb.v

TOPLEVEL = tb
COCOTB_TEST_MODULES = test.test_spi

.DEFAULT_GOAL := run

include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: run
run: sim
ifeq ($(GATES),yes)
	@python3 normalize_results.py results.xml
endif
