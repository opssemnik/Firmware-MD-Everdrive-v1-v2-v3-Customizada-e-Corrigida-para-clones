# Firmware MD Everdrive v1 & v3 Customizada e Corrigida para clones

Sistema operacional (OS) customizado em **português do Brasil** para os flashcarts
**EverDrive-MD v1** e **EverDrive-MD v3** de Mega Drive / Genesis, incluindo os clones vendidos
no Brasil e no exterior. Feito para o **Grupo RetroGamer Poa** por **Antonio e the Nobre**.

![Menu principal (v1)](v1mod/screens/menu_principal.png)

| Cartucho | Arquivo | Base | SHA-256 |
|---|---|---|---|
| EverDrive-MD **v1** | [`OS-V38-PTBR.BIN`](OS-V38-PTBR.BIN) | OS v38 (dump de um v1 clone) + logo RetroGamer POA + carregador da extensão | `d279bc9f703ad21e8577a67aa73716f7b9313f64617dded169322bddc1a6727b` |
| EverDrive-MD **v1** (extensão) | [`V1EXT.BIN`](V1EXT.BIN) (no cartão: `/EDMD/V1EXT.BIN`) | todo o mod da v1 | `0cd8b887cfc90e09441496728fc8b1f28ba3514fa8eba97128265465f96f35ce` |
| EverDrive-MD **v3** | [`MDOS.ptbr.BIN`](MDOS.ptbr.BIN) (na release: `MDOS.BIN`) | `MDOS.patched` (OS v3 já usado em clones) | `327d0b76584bb63640bc87845f4dd03b7b4541f366087f8c19e7914b0f82dba5` |

**Releases** ([página de Releases](../../releases)), 4 arquivos:

| Arquivo | O que é |
|---|---|
| `SD-EverDrive-v1.zip` | **v1**, para a raiz do cartão SD: `OS-V38-PTBR.BIN` (o firmware, para gravar uma vez) e a pasta `EDMD` com `V1EXT.BIN` (a extensão, com todo o mod), capas, banner e wallpaper |
| `SD-EverDrive-v1-sem-capas.zip` | **v1**, só o firmware e a extensão (`OS-V38-PTBR.BIN` + `EDMD/V1EXT.BIN`) |
| `MDOS.BIN` | firmware da **v3**, já com o nome certo |
| `SD-EverDrive-v3.zip` | **v3**, para a raiz do cartão SD: `EDMD/MDOS.BIN` (o firmware), capas, banner e wallpaper |

> ⚠️ Projeto independente, sem relação com a Krikzz. O EverDrive e o OS original são obra de
> Igor Golubovskiy (krikzz.com). Use por sua conta e risco. **Nenhuma ROM está incluída.**

---

## Recursos

As duas versões têm o mesmo conjunto de recursos, adaptado a cada hardware:

- **Tudo em português**, com acentos (á à â ã é ê í ó ô õ ú ç) desenhados no estilo da fonte original
- **Banner "RETROGAMER POA"** no topo da lista de jogos e dos menus, e tela de créditos com o grupo;
  pode ser trocado por uma **imagem sua** (veja [Banner personalizado](#banner-personalizado))
- **Jogos recentes** e **Favoritos**, salvos no cartucho (sobrevivem ao desligar). Só ROMs entram
  nos recentes; o último item da lista, **[ LIMPAR RECENTES ]** (com uma faixa vermelha atrás), apaga a lista
- **Jogo aleatório**: sorteia uma ROM da sua coleção
- **Busca em todas as pastas**: pela primeira letra ou por palavras do nome, digitadas num teclado na
  tela; os resultados viram uma lista normal (capa, menu do jogo, START para jogar) e B volta para a
  pasta onde você estava
- **Capas (box art)** dos jogos, lidas de `/EDMD/ART` no cartão SD
- **Info da ROM**: nome, console, copyright, serial, região, checksum e tamanho lidos do cabeçalho SEGA
- **4 temas de cores**: PADRÃO, RG POA, SEGA 16 e OUTRUN
- **Wallpaper** atrás da lista de jogos e dos menus (veja [Wallpaper](#wallpaper)), com uma arte
  retrô própria inclusa, livre para compartilhar

| | | |
|---|---|---|
| ![Lista com capa](v1mod/screens/lista_com_capa.png) | ![Menu do jogo](v1mod/screens/menu_do_jogo.png) | ![Info da ROM](v1mod/screens/info_da_rom.png) |
| Capa aparece ao parar sobre um jogo (v1) | Menu do jogo (botão A) | Info da ROM |

![Temas](v1mod/screens/temas.png)

| | |
|---|---|
| ![Wallpaper v1](v1mod/screens/lista_wallpaper.png) | ![Wallpaper v3](v3/screens/lista_wallpaper.png) |
| Banner e wallpaper inclusos (v1) | Banner e wallpaper inclusos (v3) |

---

## EverDrive-MD v1

### Instalação
1. Extraia o `SD-EverDrive-v1.zip` (ou o `-sem-capas`) da release na raiz do cartão SD: ele traz o
   `OS-V38-PTBR.BIN` e o `EDMD/V1EXT.BIN`.
2. No cartucho: **Ferramentas → gravar OS** (no OS original: *toolbox → update OS*), escolha o
   `OS-V38-PTBR.BIN` e confirme. O console reinicia sozinho.
3. No primeiro boot aparece "Atualizando o mod PT-BR..." por cerca de 1 segundo: a extensão é copiada
   do cartão para o cartucho.

**Atualizações:** o `OS-V38-PTBR.BIN` é só um carregador; todo o mod fica no `EDMD/V1EXT.BIN`. Para
atualizar, basta trocar esse arquivo no cartão: no boot seguinte o cartucho vê que mudou e copia a
versão nova sozinho. Só é preciso gravar o OS de novo quando a release disser.

**Sem a extensão** (arquivo apagado e nunca instalado) o cartucho roda o OS original, em inglês.
Segurando **B** ao ligar, ele também ignora a extensão e abre o OS original (útil se uma extensão nova
der problema: troque o arquivo no cartão e ligue de novo).

### Recuperação (se algo der errado)
Segure **A + B + C** ao ligar o console. Abre o *OS repair tool* do boot loader, que grava qualquer
OS de 64 KB a partir do cartão SD (por exemplo o seu OS original). O boot loader não confere
checksum, então o cartucho não fica "brickado".

### Controles no navegador de jogos
| Botão | Ação |
|---|---|
| Cima / Baixo | move o cursor (parado ~0,3 s sobre uma ROM, a capa aparece no centro à direita) |
| Esquerda / Direita | troca de página |
| **START** | carrega e joga na hora |
| **A** | numa pasta: entra; num jogo: abre o **menu do jogo** com a capa |
| B | volta |
| **C** | **busca em todas as pastas** (menos `EDMD`): **por nome** (teclado na tela: A digita, B apaga, START busca; várias palavras = todas precisam aparecer, em qualquer ordem) ou **pela primeira letra**. Os resultados (até 512) aparecem como uma pasta, com `[*]` ao lado da página; **B** volta para a pasta onde você estava. B durante a busca para |

Menu do jogo: **Carregar e jogar**, **Só carregar**, **Jogar com cheats**, **Adicionar aos favoritos**,
**Info da ROM**, **Voltar**. *Jogar com cheats* carrega o jogo, abre o menu de códigos Game Genie (digite ou
carregue os códigos e use *aplicar*) e, ao sair dele, inicia o jogo.
**ESQ/DIR** no menu do jogo vai para o jogo anterior/seguinte da pasta (pula pastas e arquivos que não são ROM).

Menu principal: Jogar último jogo · Selecionar jogo · Jogos recentes · Favoritos · Jogo aleatório ·
Opções · Cheats · Ferramentas · Tema. A versão do mod aparece no rodapé (**PT-BR 1.22**) e em Ferramentas → dispositivo.

### Detalhes
- Recentes e Favoritos (8 de cada) ficam no mesmo bloco de flash das opções (`0x30000`); a flash só é regravada quando a lista muda.
- Antes de carregar um recente/favorito o OS confere se o arquivo ainda é o mesmo no cartão; se você apagou ou trocou, aparece "Arquivo não encontrado no SD" em vez de carregar lixo.
- O jogo aleatório parte da última pasta aberta e desce pelas subpastas (ignora `EDMD`), escolhendo só `.bin .md .gen .smd .sms .32x`.
- A extensão fica no bloco `0x40000` da flash do cartucho (64 KB, livre: o OS original não usa a faixa
  `0x40000-0xCFFFF`). No boot, o carregador compara o cabeçalho do `/EDMD/V1EXT.BIN` com o da cópia na
  flash e só regrava quando mudou; o cabeçalho é gravado por último, então uma cópia interrompida nunca
  passa por completa. Sem cartão, roda a cópia que já está na flash.

---

## EverDrive-MD v3

### Instalação
O v3 carrega o OS do cartão SD: o firmware fica em **`/EDMD/MDOS.BIN`**. O jeito mais fácil é extrair o
`SD-EverDrive-v3.zip` da release na raiz do cartão (já traz o `MDOS.BIN`, capas, banner e wallpaper).
Compilando você mesmo, renomeie `MDOS.ptbr.BIN` para `MDOS.BIN`. Para voltar ao original, basta recolocar o `MDOS.BIN` original.

O nome e a pasta precisam ser exatamente esses: a BIOS só carrega os primeiros 32 KB do arquivo, e as
telas de Info da ROM, Opções, Recentes/Favoritos, Créditos, *Jogar com Cheats* e a busca são lidas do
resto do próprio `MDOS.BIN` quando você as abre.

### Controles
| Botão | Ação |
|---|---|
| Esquerda / Direita | troca de página |
| START | repete o último jogo |
| **A** | menu do arquivo em tela cheia, com o nome do jogo e a capa (Carregar e Jogar, Só Carregar, Jogar com Cheats, Favoritar Jogo, Info da ROM, Ver em Hex); dentro dele, **ESQ/DIR** vai para o jogo anterior/seguinte |
| B | volta |
| **C** | menu principal: **Buscar em Todas as Pastas** (o primeiro item: C e A), Opções, Jogos Recentes, Favoritos, Jogo Aleatório, Cheats, Info Sistema, Créditos. A busca funciona como na v1: por nome (teclado na tela) ou pela primeira letra; os resultados (até 512) aparecem como uma pasta, com `[*]` ao lado da página, e **B** volta para a pasta onde você estava |

**Capa na lista:** parado ~0,3 s sobre um jogo, a capa aparece no centro à direita da lista;
qualquer botão a remove (a página é redesenhada). Rolar rápido não carrega nada.

![Capa na lista (v3)](v3/screens/lista_com_capa.png)

O tema visual fica em **Opções → Tema Visual**. Recentes/Favoritos (10 de cada) ficam na SRAM do cartucho. Em **Info Sistema** a versão aparece como **PT-BR 1.22**.

---

## Banner personalizado

O banner do topo (lista de jogos, menus, menu do jogo, Info da ROM) pode ser uma imagem colorida.
Sem o arquivo, aparece o banner "RETROGAMER POA" padrão. O repositório e os zips da release já trazem
um banner retrô próprio em `sd/EDMD/BANNER.ART` (gerado por [`arte/gen_arte.py`](arte/gen_arte.py)).

- Tamanho: **288×24 px** (36×3 tiles), até **13 cores** (a paleta do Mega Drive tem 512 cores; o
  conversor ajusta). A cor 1 da paleta fica reservada para o vermelho da faixa de destaque dos menus.
  Use um fundo opaco: a imagem é desenhada inteira.
- Converta e copie para o cartão SD em **`/EDMD/BANNER.ART`** (vale para v1 e v3):

```
pip install pillow
python make_banner.py meu_banner.png E:\EDMD\BANNER.ART
```

Imagens de outro tamanho são redimensionadas e cortadas no centro. Pixel art com até 13 cores fica
idêntica; imagens com mais cores são reduzidas para 13. `BANNER.ART` gerados antes da versão 1.11
precisam ser convertidos de novo.

## Wallpaper

Uma imagem atrás da lista de jogos e dos menus, em `/EDMD/WALL.ART` (vale para v1 e v3). Sem o
arquivo, o fundo continua liso. O repositório e os zips da release já trazem um wallpaper retrô
próprio (`sd/EDMD/WALL.ART`, de [`arte/gen_arte.py`](arte/gen_arte.py)).

- Tamanho **320×224 px**, até **14 cores**; o preto puro fica transparente e mostra a cor de fundo do tema.
- Use uma imagem **escura**: o texto da lista fica por cima. O conversor escurece com `--dim`.
- Cabem até **800 tiles** diferentes (8×8). Pixel art e padrões repetidos cabem fácil; numa foto o
  conversor junta os tiles mais parecidos até caber, perdendo um pouco de detalhe.

```
pip install pillow
python make_wallpaper.py meu_wallpaper.png E:/EDMD/WALL.ART --dim 0.55
```

## Capas (box art)

O repositório já traz **2176 capas prontas** em [`sd/EDMD/ART`](sd/EDMD/ART) (também dentro dos
`SD-EverDrive-v1.zip` / `SD-EverDrive-v3.zip` da página de Releases).

**Onde colocar:** copie a pasta `EDMD` de dentro de `sd/` para a **raiz do cartão SD**, ficando assim:

```
Cartão SD (E:\)
├── EDMD\
│   ├── BANNER.ART        (banner, opcional)
│   ├── WALL.ART          (wallpaper, opcional)
│   ├── MDOS.BIN          (só v3: o firmware)
│   ├── ART\
│   │   ├── 0C4F65A0.ART
│   │   ├── 3F75B964.ART
│   │   └── ...           (2176 arquivos)
│   └── SAVE\             (já existe; é onde o OS guarda os saves)
└── (suas pastas de ROMs, em qualquer lugar)
```

Se já existir uma pasta `EDMD` no cartão, só junte o conteúdo (não apague a `SAVE`). As ROMs podem
ficar em qualquer pasta; a capa é encontrada pelo conteúdo da ROM, não pelo nome do arquivo.

Ambas as versões (v1 e v3) usam o mesmo formato: `/EDMD/ART/XXXXXXXX.ART`, onde `XXXXXXXX` é um
hash dos primeiros 512 bytes da ROM (12×9 tiles, 14 cores). Se algum jogo seu não tiver capa
(dump diferente, hack, tradução), gere as que faltam a partir das imagens da Libretro:

```
pip install pillow
python sync_roms_art.py "E:\ROMS"          # cria E:\ROMS\EDMD\ART\*.ART só para o que faltar
```

As imagens originais vêm do projeto [libretro-thumbnails](https://github.com/libretro-thumbnails).

---

## Compilando

Os arquivos originais **não** estão no repositório. Coloque-os na pasta do projeto:

| Para | Arquivos necessários |
|---|---|
| v1 (`build_v1_ptbr.py`) | `OS-V38.BIN` (dump do seu v1), `os-v36-retrogamer-poa.bin` (bloco do logo RetroGamer POA) |
| v3 (`build_custom_mdos.py`) | `MDOS.patched.BIN` |

**v1** — o código novo é C + assembly em [`v1mod/`](v1mod), compilado com GCC m68k no WSL (Debian).
`loader.c` é o carregador que vai no OS; o resto (`mod.c`, `search.c`, `hooks.S`) vira o `V1EXT.BIN`,
junto com a tabela de alterações do OS em RAM (tradução e ganchos) que a extensão aplica no boot:

```
# dentro do WSL (ou sem root: apt-get download + dpkg -x, veja v1mod/build.sh)
sudo apt install gcc-m68k-linux-gnu binutils-m68k-linux-gnu
# no Windows
pip install capstone
python build_v1_ptbr.py          # gera OS-V38-PTBR.BIN + V1EXT.BIN (extensão) e confere todos os patches
```

O script verifica cada byte original antes de alterar (a extensão confere de novo no cartucho, antes de
aplicar) e só muda o `OS-V38-PTBR.BIN` quando o carregador muda.

**Testes (v1)** — `v1mod/test/` roda o OS de verdade num emulador 68000 (Unicorn) com VDP, flash,
controle e cartão SD simulados, inclusive com a checagem de alinhamento de memória do 68000 real:

```
pip install unicorn==2.1.4 pillow capstone
# gera um cartão SD de teste (FAT32) via mtools/dosfstools no WSL: mkimg.py + mkimg.sh
python t_all.py all ; python t_edge.py ; python t_preview.py ; python t_mine4.py ; python t_search.py ; python t_loader.py
# v3 (emu3.py, mesmo emulador com BIOS do cartucho simulado)
python t3_preview.py ; python t3_flows.py ; python t3_lr.py ; python t3_version.py ; python t3_recent.py ; python t3_v16.py ; python t3_flicker.py ; python t3_banner.py ; python t3_ovl.py ; python t3_nomdos.py ; python t3_search.py
# rode sdput.sh (WSL) depois de compilar, para copiar o MDOS.BIN e o V1EXT.BIN novos para as imagens do SD
# banner: t_banner.py / t3_banner.py usam sd/sdb.img; wallpaper: t_wall.py v1|v3 usa sd/sdw.img
```

**v3** — assembly montado pelo próprio script, mais a busca em C ([`v3mod/`](v3mod), mesmo GCC do v1, vira a
segunda página de telas do `MDOS.BIN`). Rode a partir da pasta acima de `mega-genesis/`:

```
python mega-genesis/build_custom_mdos.py
```

### Outras ferramentas
- `build_v3_dumper.py` — gera uma ROM que faz dump do OS do cartucho v3.
- `extract_sram_dump.py` — extrai o OS de um `.SRM` gerado pelo dumper.

---

## Créditos
- **EverDrive-MD** e OS original: Igor Golubovskiy — [krikzz.com](http://krikzz.com)
- **Mod PT-BR, capas, recentes, favoritos e temas**: Antonio e the Nobre
- **Grupo RetroGamer Poa**

Veja as mudanças em [CHANGELOG.md](CHANGELOG.md).
