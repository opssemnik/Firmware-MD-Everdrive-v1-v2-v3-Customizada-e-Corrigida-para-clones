# Mudanças

## Capas
- 2176 capas `.ART` prontas em `sd/EDMD/ART` (geradas com `sync_roms_art.py` a partir da libretro-thumbnails).

## EverDrive-MD v1 — `OS-V38-PTBR.BIN`

### 1.3 — 2026-10-18
- Capa da lista agora fica em posição fixa, no centro da lateral direita.
- Espera para a capa aparecer reduzida em 20% (24 → 19 quadros, ~0,32 s em NTSC).

### 1.2 — 2026-10-18
- **Capa na lista de jogos:** ao parar ~0,4 s sobre uma ROM em "Selecionar jogo", a capa aparece
  ao lado da lista. Rolar rápido não carrega nada; qualquer botão some com a capa e cancela a leitura.
- A capa fica em cache: abrir o menu do jogo (A) depois da prévia é instantâneo.
- **Correção:** o OS v38 original confere um checksum da própria tabela de textos durante o
  carregamento de alguns jogos; a tradução apontava esse endereço para o texto traduzido e
  podia travar o carregamento. Agora a tabela original fica intacta.

### 1.1 — 2026-10-18
- **Correção:** apertar A em um jogo travava o console. Um buffer usado pela leitura do SD estava
  em endereço ímpar, o que gera *address error* no 68000 real.
- Banner "RETROGAMER POA" refeito com a fonte 8×8 do menu (dourado com sombra sobre faixa vermelha).

### 1.0 — 2026-10-18
- Base: OS v38 dumpado de um EverDrive-MD v1 clone, com o bloco do distribuidor/logo
  **RetroGamer POA**.
- Todo o OS traduzido para PT-BR, com acentos desenhados no estilo da fonte original.
- Novo menu principal: Jogar último jogo, Selecionar jogo, Jogos recentes, Favoritos,
  Jogo aleatório, Opções, Cheats, Ferramentas, Tema.
- **Menu do jogo** (A sobre um arquivo): Carregar e jogar, Só carregar, Adicionar aos favoritos,
  Info da ROM — com a capa do jogo. START continua carregando direto.
- **Jogos recentes** e **Favoritos** (8 de cada) salvos na flash junto com as opções; conferem se
  o arquivo ainda existe no cartão antes de carregar; favoritos podem ser removidos.
- **Jogo aleatório** pela coleção, descendo pelas subpastas.
- **Info da ROM** do cabeçalho SEGA (converte títulos em Shift-JIS de largura total).
- **4 temas** de cor, salvos no cartucho.
- Tela de créditos nova com o logo RetroGamer POA.
- **Correção de bug do OS original:** arquivos menores que ~19 KB causavam divisão por zero
  (travamento) ao carregar; agora aparece "Arquivo pequeno demais".
- Proteção para atualização de OS: se a gravação falhar no meio, os menus usam as rotinas
  originais e o console permanece em Ferramentas para tentar novamente.

## EverDrive-MD v3 — `MDOS.ptbr.BIN`

### 1.0 — 2026-10-17
- Base: `MDOS.patched` (OS v3 usado em clones). Versão exibida como **v40**.
- OS traduzido para PT-BR com acentos (ç ã õ á é í ó Ã).
- Banner "RETROGAMER POA" no topo do navegador e nova tela de créditos.
- Menu principal no botão C: Opções, Jogos Recentes, Favoritos, Jogo Aleatório, Cheats,
  Info Sistema, Créditos.
- Menu do arquivo no botão A com capa do jogo: Carregar e Jogar, Só Carregar, Favoritar Jogo,
  Info da ROM, Ver em Hex.
- Jogos Recentes e Favoritos (10 de cada) salvos na SRAM.
- Opção "Tema Visual" com 4 temas (PADRÃO, RG POA, SEGA 16, OUTRUN).
- Ferramenta `sync_roms_art.py` para baixar capas da Libretro e gerar os arquivos `.ART`.
