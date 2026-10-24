/* v3 overlay page 2 (search.c): loaded by ovlEnter into the box-art buffer 0xFFC800 (7 sectors) */
MEMORY
{
    OVL (rx) : ORIGIN = 0xFFC800, LENGTH = 0x0E00
}

SECTIONS
{
    .ovl : { KEEP(*(.entry)) *(.text .text.*) *(.rodata .rodata.*) } > OVL
    .data : { *(.data .data.*) *(.bss .bss.* COMMON) } > OVL
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) *(.gnu*) }
}
