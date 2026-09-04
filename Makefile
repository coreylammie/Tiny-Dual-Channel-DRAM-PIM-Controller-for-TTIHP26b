TOPLEVEL_LANG ?= verilog
SIM ?= icarus
TOPLEVEL := tt_um_tiny_dram_pim
COCOTB_TEST_MODULES ?= test.test_spi

VERILOG_SOURCES := \
	$(PWD)/src/pim_pkg.sv \
	$(PWD)/src/command_decoder.sv \
	$(PWD)/src/spi_frontend.sv \
	$(PWD)/src/pim_channel.sv \
	$(PWD)/src/tt_um_tiny_dram_pim.sv

include $(shell cocotb-config --makefiles)/Makefile.sim
