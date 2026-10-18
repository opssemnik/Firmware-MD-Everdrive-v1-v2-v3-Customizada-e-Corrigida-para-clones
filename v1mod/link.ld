/*
 * Free space inside the OS flash image (cart address = file offset + 0x10000).
 * ROMC/ROMB: blank rows of the RetroGamer POA distributor logo (only rows 2-4 are drawn).
 * ROMA: after the OS variable block up to the 8-byte build signature at 0x1FFF8.
 * RAM: above the OS variables (0xFFE336); the file bytes copied there at boot are unused.
 */
MEMORY
{
    ROMC (rx) : ORIGIN = 0x1C220, LENGTH = 0x0A00
    ROMB (rx) : ORIGIN = 0x1DB20, LENGTH = 0x07A0
    ROMA (rx) : ORIGIN = 0x1E400, LENGTH = 0x1BF8
    ROMD (rx) : ORIGIN = 0x1CC20, LENGTH = 0x0F00     /* POA logo rows 2-4: diagnostics build only */
    RAM  (rw) : ORIGIN = 0xFFE400, LENGTH = 0x0C00
}

SECTIONS
{
    .text : { *(.text .text.*) *(.rodata .rodata.*) } > ROMA
    .strb : { *(.strb) } > ROMB
    .diag : { *(.diag) *(.diagro) } > ROMD
    .strc : { *(.strc) } > ROMC
    .ramstub : { *(.ramstub) } > RAM AT > ROMA
    .data : { *(.data .data.*) } > RAM AT > ROMA
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
