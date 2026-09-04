"""cocotb SPI helper for the Stage 1 frontend."""


class SpiDriver:
    def __init__(self, dut, half_period_cycles=2):
        self.dut = dut
        self.half_period_cycles = half_period_cycles

    async def _wait_core(self):
        from cocotb.triggers import RisingEdge

        for _ in range(self.half_period_cycles):
            await RisingEdge(self.dut.clk)

    async def transfer32(self, word: int) -> int:
        self.dut.ui_in.value = int(self.dut.ui_in.value) | 0x02
        await self._wait_core()
        self.dut.ui_in.value = int(self.dut.ui_in.value) & ~0x02
        await self._wait_core()

        read = 0
        for bit in range(31, -1, -1):
            mosi = (word >> bit) & 1
            base = int(self.dut.ui_in.value) & ~0x05
            self.dut.ui_in.value = base | (mosi << 2)
            await self._wait_core()
            self.dut.ui_in.value = base | 0x01 | (mosi << 2)
            await self._wait_core()
            read = (read << 1) | (int(self.dut.uo_out.value) & 0x01)
            self.dut.ui_in.value = base | (mosi << 2)
            await self._wait_core()

        self.dut.ui_in.value = int(self.dut.ui_in.value) | 0x02
        await self._wait_core()
        return read & 0xFFFFFFFF
