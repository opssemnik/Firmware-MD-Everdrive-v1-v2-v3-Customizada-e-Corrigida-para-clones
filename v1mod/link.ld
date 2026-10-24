/*
 * BASE: the loader, in the OS image after the OS variable block (cart = file offset + 0x10000), up to the
 *       8-byte signature at 0x1FFF8.
 * EXT:  the flash extension (/EDMD/V1EXT.BIN), copied to cart 0x40000 by the loader: header, all the
 *       mod code and data, the RAM stubs (copied to RAM by myInit) and the OS patch table.
 * RAM:  above the OS variables (0xFFE336); the file bytes copied there at boot are unused.
 */
MEMORY
{
    BASE (rx) : ORIGIN = 0x1E400, LENGTH = 0x1BF8
    EXT  (rx) : ORIGIN = 0x40000, LENGTH = 0x10000
    RAM  (rw) : ORIGIN = 0xFFE400, LENGTH = 0x0C00
}

SECTIONS
{
    .base : { build/loader.o(.text .text.* .rodata .rodata.*) } > BASE
    .ext : { KEEP(*(.exthdr)) *(.text .text.*) *(.rodata .rodata.*) . = ALIGN(4); } > EXT
    .ramstub : { *(.ramstub) } > RAM AT > EXT
    .patch : { KEEP(*(.patch)) } > EXT
    .data : { *(.data .data.*) } > RAM AT > EXT
    .bss (NOLOAD) : { bssStart = .; *(.bss .bss.* COMMON) bssEnd = .; } > RAM
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) *(.gnu*) }
}

ramStubStart = LOADADDR(.ramstub);
ramStubEnd = LOADADDR(.ramstub) + SIZEOF(.ramstub);
ramStubRam = ADDR(.ramstub);

/* libgcc helpers already present in the OS */
__mulsi3 = 0xFF929C;
__udivsi3 = 0xFF92C0;
__divsi3 = 0xFF931C;
__umodsi3 = 0xFF934C;
__modsi3 = 0xFF937C;
