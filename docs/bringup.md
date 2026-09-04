# Physical Bring-Up

TinyTapeout does not add a project-specific SPI peripheral to the design. The
chip wrapper exposes the standard project pins, and this project implements its
own SPI slave on top of those pins.

## Pin Mapping

| Signal | TinyTapeout pin | Direction | Meaning |
|---|---|---|---|
| `clk` | `clk` | input | project clock |
| `rst_n` | `rst_n` | input | active-low reset |
| `ena` | `ena` | input | project enable from the TT wrapper |
| `spi_sclk` | `ui_in[0]` | input | SPI serial clock |
| `spi_cs_n` | `ui_in[1]` | input | SPI chip-select, active low |
| `spi_mosi` | `ui_in[2]` | input | SPI host-to-project data |
| `spi_miso` | `uo_out[0]` | output | SPI project-to-host data |

The remaining `uo_out` bits expose compact debug status:

| TinyTapeout pin | Meaning |
|---|---|
| `uo_out[1]` | channel 0 bank 0 open |
| `uo_out[2]` | channel 0 bank 1 open |
| `uo_out[3]` | channel 0 refresh busy |
| `uo_out[4]` | channel 1 bank 0 open |
| `uo_out[5]` | channel 1 bank 1 open |
| `uo_out[6]` | channel 1 refresh busy |
| `uo_out[7]` | enable monitor |

`uio[7:0]` is unused and driven with output-enable low.

## Interaction Model

After tapeout, the TinyTapeout demoboard or an external host can interact with
the project by selecting the design, providing `clk`, releasing `rst_n`, and
toggling the SPI pins above. Each transaction is a 32-bit command word sent
MSB-first. Read data and status are returned on the following 32-bit SPI frame.

This maps directly to the cocotb driver in `test/model/spi_driver.py`, which
bit-bangs `ui_in[0]`, `ui_in[1]`, and `ui_in[2]`, then samples `uo_out[0]`.

## TinyTapeout SPI Pinout Note

TinyTapeout recommends common peripheral pinouts where possible. The common SPI
PMOD mapping uses the bidirectional `uio` pins so that one PMOD row can carry
CS, MOSI, MISO, and SCK. This project instead uses dedicated input pins for
SCLK/CS/MOSI and a dedicated output pin for MISO. That keeps the RTL simpler and
leaves `uio` unused, but it means a small adapter or custom demoboard script is
needed for PMOD-style SPI hardware.
