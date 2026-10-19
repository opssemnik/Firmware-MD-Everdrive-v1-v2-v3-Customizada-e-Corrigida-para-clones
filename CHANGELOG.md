# Mudanças

## Capas
- 2176 capas `.ART` prontas em `sd/EDMD/ART` (geradas com `sync_roms_art.py` a partir da libretro-thumbnails).

## EverDrive-MD v1 — `OS-V38-PTBR.BIN`

### 1.10 — 2026-10-18
- O item **[ LIMPAR RECENTES ]** ficou destacado (maiúsculas entre colchetes) no fim da lista de recentes.

### 1.9 — 2026-10-18
- **Banner com imagem**: `/EDMD/BANNER.ART` (288×24 px, até 14 cores, gerado com `make_banner.py`)
  aparece no topo dos menus, do menu do jogo e da lista de jogos. Sem o arquivo, fica o banner padrão.
- A **lista de jogos ganhou o banner**: desceu uma linha (lista nas linhas 3-23, página na 24, nome
  do arquivo na 25-26) para abrir espaço no topo.

### 1.8 — 2026-10-18
- Sem mudanças de código; só a versão (mesma numeração da v3).

### 1.7 — 2026-10-18
- Sem mudanças de código; só a versão (mesma numeração da v3).

### 1.6 — 2026-10-18
- Só ROMs (`.bin .md .gen .smd .sms .32x`) entram nos **Jogos recentes**: um `.rar` ou outro
  arquivo carregado por engano não aparece mais na lista.
- **Limpar recentes**: último item da lista de recentes; apaga só os recentes (favoritos e opções ficam).

### 1.5 — 2026-10-18
- Versão exibida só como **PT-BR 1.5** (rodapé do menu principal e Ferramentas → dispositivo),
  mesma numeração da v3.

### 1.4 — 2026-10-18
- **ESQ/DIR no menu do jogo** (botão A num jogo): vai para o jogo anterior/seguinte da pasta,
  pulando pastas e arquivos que não são ROM; ao sair, o cursor da lista fica nesse jogo.
- **Versão do mod junto da versão do OS**: "PT-BR 1.4 OS v38" no rodapé do menu principal e em
  Ferramentas → dispositivo.
- Jogos com nome longo cortado pelo OS (nome atravessando setor do diretório) agora contam como
  ROM no jogo aleatório e na navegação.
- Build de diagnóstico (`build_v1_ptbr.py --diag`): cronômetro de carregamento e dados da flash.

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

### 1.10 — 2026-10-18
- O item **[ LIMPAR RECENTES ]** ficou destacado (maiúsculas entre colchetes) no fim da lista de recentes.

### 1.9 — 2026-10-18
- **Banner com imagem**: o mesmo `/EDMD/BANNER.ART` da v1, no topo da lista de jogos, do menu do
  arquivo e da Info da ROM. Sem o arquivo, fica o banner padrão.
- A barra cinza do topo da lista saiu: o banner fica sobre o fundo preto, como na v1.
- A capa e o banner usam o mesmo carregador de `.ART`; código compactado para caber.

### 1.8 — 2026-10-18
- **Correção:** a tela de créditos mostrava "repetir óltimo jogo". A fonte ganhou o "ú" (no lugar do
  "í", que nenhum texto da v3 usa).

### 1.7 — 2026-10-18
- **Correção: piscada ao trocar de jogo com ESQ/DIR no menu do arquivo.** A lista de jogos era
  redesenhada (e aparecia por um instante) antes de abrir o menu do próximo jogo; agora a tela vai
  direto de um menu para o outro, e a lista só é redesenhada ao sair do menu.

### 1.6 — 2026-10-18
- **"Pág. x de y" embaixo**, logo acima da barra com o nome do arquivo, como na v1. A barra de cima
  fica só com o banner.
- **Menu do arquivo em tela cheia** (igual à v1): banner, nome do jogo centralizado, menu e capa;
  a lista não aparece mais por trás. ESQ/DIR troca de jogo e atualiza o nome.
- Só ROMs entram nos **Jogos Recentes**; o **Jogo Aleatório** também só sorteia ROMs.
- **Limpar recentes**: último item da lista de recentes.
- A lista de recentes/favoritos foi reescrita menor, para abrir espaço para isso.

### 1.5 — 2026-10-18
- Versão exibida só como **PT-BR 1.5** em Info Sistema (antes "PT-BR 1.2 OS v40"); a v3 pula de 1.2
  para 1.5 para ficar com a mesma numeração da v1.

### 1.2 — 2026-10-18
- **Correção: capa na lista não aparecia no cartucho.** A tela da v3 usa buffer duplo; a prévia
  desenhava no buffer oculto. Agora ela chama o repaint.
- **Banner centralizado de 16 tiles**, igual ao da v1; o topo do navegador virou uma barra de
  2 linhas com "Pág. x de y" na segunda.
- Tiles da capa movidos para 0x100+ (desenhados direto na tabela de nomes), liberando espaço
  para o banner.
- **ESQ/DIR no menu do arquivo**: jogo anterior/seguinte da pasta; a lista acompanha.
- **Versão do mod em Info Sistema**: "PT-BR 1.2 OS v40".
- Código novo ocupa também as áreas dos textos em inglês que deixaram de ser usados.

### 1.1 — 2026-10-18
- **Capa na lista de jogos** (porte da v1): parado ~0,3 s sobre um jogo, a capa aparece no centro
  à direita; qualquer botão redesenha a página e remove a capa. Rolar rápido não carrega nada.
- **Banner "RETROGAMER POA" legível**: fonte 8x8 do menu (passo de 7 px para caber em 12 tiles),
  dourado com sombra sobre a faixa vermelha.
- Carregamento da capa e desenho dos tiles viraram sub-rotinas compartilhadas entre o menu do
  arquivo e a prévia.

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
