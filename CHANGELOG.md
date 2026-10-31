# Mudanças

## Capas
- `sd/EDMD/BANNER.ART` e `sd/EDMD/WALL.ART`: banner e wallpaper retrô próprios (desde a 1.14).
- 2176 capas `.ART` prontas em `sd/EDMD/ART` (geradas com `sync_roms_art.py` a partir da libretro-thumbnails).

## EverDrive-MD v1 / v2 — `OS-V38-PTBR.BIN`

### 1.26 — 2026-10-30
- Sem mudanças além da versão (mesma numeração da v3). Quem já está na 1.22 ou mais nova só troca o `EDMD/V1EXT.BIN`.

### 1.25 — 2026-10-24
- O firmware nos zips agora leva a versão no nome: **`OS-V38-PTBR-1.25.BIN`** (o conteúdo é o mesmo carregador desde a 1.22: quem já gravou não precisa gravar de novo, só trocar o `EDMD/V1EXT.BIN`).

### 1.24 — 2026-10-24
- Sem mudanças além da versão (mesma numeração da v3). Quem já está na 1.22 ou 1.23 só troca o `EDMD/V1EXT.BIN`.

### 1.23 — 2026-10-24
- **Cores no banner:** um `BANNER.ART` pode trazer as cores do tema (fundo, faixa do menu, texto); com ele, essas cores valem no lugar do tema escolhido e o menu mostra **Tema: DO BANNER**. Novo `make_banner.py --cores`.
- Primeiro tema pronto: **Maddrugamers** (`Tema-Maddrugamers.zip`), veja abaixo.
- Só o `V1EXT.BIN` mudou: quem já gravou o OS da 1.22 só precisa trocar o `EDMD/V1EXT.BIN` no cartão.

### 1.22 — 2026-10-24
- **Nova arquitetura: OS + extensão.** O `OS-V38-PTBR.BIN` agora é só um carregador; todo o mod (tradução, menus, capas, busca...) fica em `/EDMD/V1EXT.BIN`. No boot, o cartucho compara o arquivo do cartão com a cópia na flash (bloco `0x40000`) e regrava só quando mudou (~1 s, "Atualizando o mod PT-BR..."). **Grave este OS uma vez** (Ferramentas → gravar OS); as próximas versões poderão vir só como um `V1EXT.BIN` novo.
- Sem a extensão (nunca instalada) roda o OS original, em inglês. Segurar **B** ao ligar também abre o OS original (para escapar de uma extensão com problema).
- **C na lista de jogos agora abre direto a busca em todas as pastas** (por nome ou pela primeira letra). O filtro por letra da pasta foi removido: as pastas já são paginadas.
- **B nos resultados volta para a pasta onde você estava**, com o cursor no mesmo jogo. Uma busca nova a partir dos resultados troca a lista no mesmo nível.
- Barra de ajuda alinhada com a lista: `A: menu   START: jogar    C: buscar`.

### 1.21 — 2026-10-24
- **Busca em todas as pastas**: botão **C** na lista de jogos → *Buscar em todas as pastas*. Procura no cartão inteiro (menos `EDMD`) **por letra** ou **por nome**, num teclado na tela (A digita, B apaga, START busca; várias palavras precisam aparecer todas, em qualquer ordem). Os resultados (até 512) aparecem como uma pasta, com `[*]` ao lado da página: capa, menu do jogo e START funcionam como sempre. B ou "Todos" voltam às pastas; B durante a busca para.
- A busca fica numa **extensão**, `/EDMD/V1EXT.BIN` (vem no `SD-EverDrive-v1.zip`): na primeira busca ela é copiada para um bloco livre da flash do cartucho (`0x40000`, ~1 s). Sem o arquivo aparece "Falta /EDMD/V1EXT.BIN" e o resto funciona normalmente.
- Barra de ajuda: `A: menu  START: jogar  C: filtro/busca`.

### 1.20 — 2026-10-19
- **Barra de ajuda** logo abaixo do banner na lista de jogos: `A: menu   START: jogar   C: filtrar`.

### 1.19 — 2026-10-19
- **Filtro por letra**: botão **C** na lista de jogos. Escolha o grupo e a letra; a pasta passa a mostrar só os jogos que começam com ela (as pastas continuam), com `[M]` ao lado da página. "Todos" tira o filtro; trocar de pasta também. Letra sem jogos mostra um aviso e mantém a lista.
- **Correção**: depois de uma capa aparecer na lista, entrar numa subpasta e voltar com B podia levar a `/EDMD/ART` (a busca da capa no SD mudava a "pasta atual" do navegador). Agora a pasta é preservada.

### 1.18 — 2026-10-19
- **Margem antes do rodapé**: uma linha vazia entre o último jogo da página e a página (lista nas linhas 4-24, linha 25 vazia, página na 26).
- A barra com o nome do arquivo ficou com **1 linha** (a 27): o nome mostra até 38 letras numa linha só, em vez de quebrar em duas.

### 1.17 — 2026-10-19
- **Rodapé da lista de jogos**: "pág: x / y" em dourado e a barra com o nome do arquivo no vermelho do banner (antes cinza), com o nome em branco por cima.

### 1.16 — 2026-10-19
- Sem mudanças de código; só a versão (mesma numeração da v3). O build agora recusa instruções de leitura-e-escrita nas portas do vídeo (a causa da tela preta da v3).

### 1.15 — 2026-10-19
- **Jogar com cheats**: o START na lista de códigos agora aplica os códigos e inicia o jogo (aparece "pronto"; aperte um botão). Antes ele só aplicava e voltava ao menu de cheats.
- **Barra de progresso no "apagando..."** ao carregar um jogo: enche pelo tempo estimado (~7,4 ms por KB, medido no cartucho) e completa quando a flash termina.
- Uma linha a mais entre o banner e o nome do jogo no menu do jogo e na tela Info da ROM.

### 1.14 — 2026-10-19
- **Wallpaper**: `/EDMD/WALL.ART` (320×224, até 14 cores, gerado com `make_wallpaper.py`) atrás da
  lista de jogos e dos menus. Mesmo arquivo para v1 e v3.
- Banner e wallpaper retrô próprios (livres para compartilhar) em `sd/EDMD`, gerados por `arte/gen_arte.py`.
- O banner de imagem passou para a VRAM 0x2E00 (mesmo lugar da v3); o wallpaper usa 0x3B80-0x9FFF.

### 1.13 — 2026-10-19
- **Jogar com cheats** no menu do jogo (botão A): carrega o jogo, abre o menu de códigos Game Genie
  e, ao sair dele, inicia o jogo com os códigos aplicados.

### 1.12 — 2026-10-18
- **Espaço entre o banner e a lista de jogos**: uma linha em branco embaixo do banner. A lista
  ocupa as linhas 4-24, a página fica na 25 e a barra com o nome do arquivo nas linhas 26-27.
- A capa da pré-visualização desceu uma linha para continuar no meio da lista.

### 1.11 — 2026-10-18
- **[ LIMPAR RECENTES ]** ganhou uma faixa vermelha atrás da linha (como o rodapé), na largura da tela.
- `make_banner.py` reserva a cor 1 do banner para essa faixa: converta de novo o `BANNER.ART`.

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

### 1.26 — 2026-10-30
- Novo **Unbrick - Recuperar** (`Unbrick-Recuperar-EverDrive-v3.zip`, à parte): o OS PT-BR com o reparo do setor de boot para cartuchos v3 travados pela proteção do OS original ("EverDrive clone detected ... Device locked permanently"). Na lista de jogos ele confere o boot; se estiver diferente, **A** regrava e confere os 64 KB. Depois é só voltar para o `MDOS.BIN` normal.

### 1.25 — 2026-10-24
- Sem mudanças além da versão (mesma numeração da v1 / v2).

### 1.24 — 2026-10-24
- **Barra de ajuda alinhada com a lista**: agora termina na mesma coluna dos tamanhos dos jogos (`1M`..`4M`), sem passar do fim: `A: arquivo  START: repetir  C: menu`.

### 1.23 — 2026-10-24
- **Cores no banner:** um `BANNER.ART` pode trazer as cores do tema; com ele, essas cores valem no lugar do tema escolhido em Opções.
- Primeiro tema pronto: **Maddrugamers** (`Tema-Maddrugamers.zip`).

**Tema Maddrugamers** (arquivo separado, `Tema-Maddrugamers.zip`, para v1 e v3): banner, wallpaper e cores para o canal [youtube.com/@maddrugamers](https://www.youtube.com/@maddrugamers) - preto, letreiro verde com sombra 3D e joysticks estilo arcade. Extraia na raiz do cartão SD (substitui `EDMD/BANNER.ART` e `EDMD/WALL.ART`).

### 1.22 — 2026-10-24
- **Busca em todas as pastas** (C → *Buscar em Todas as Pastas*, o primeiro item do menu): por nome, num teclado na tela (várias palavras: todas precisam aparecer), ou pela primeira letra. Os resultados (até 512) aparecem como uma pasta, com `[*]` ao lado da página; capa, menu do arquivo e START funcionam normalmente, e **B** volta para a pasta onde você estava.
- O **Filtrar por Letra** foi removido (substituído pela busca).
- Barra de ajuda alinhada com a lista: `A: arquivo   START: repetir   C: menu` (até a 1.23 passava 2 colunas do fim da lista).

### 1.21 — 2026-10-24
- Sem mudanças de código; só a versão (mesma numeração da v1). A busca em todas as pastas chega à v3 na próxima versão.

### 1.20 — 2026-10-19
- **Barra de ajuda** logo abaixo do banner na lista de jogos: `A: arquivo  START: repetir  C: filtro` (o C abre o menu principal, onde fica o Filtrar por Letra).

### 1.19 — 2026-10-19
- **Filtro por letra**: novo item **Filtrar por Letra** no menu principal (botão C). Escolha o grupo e a letra; a pasta passa a mostrar só os jogos que começam com ela (as pastas continuam), com `[M]` ao lado da página. "Todos" tira o filtro; trocar de pasta também.
- Correção interna: a volta do menu principal para a lista deixava 4 bytes perdidos na pilha a cada C.

### 1.18 — 2026-10-19
- **Margem antes do rodapé**: uma linha vazia entre o último jogo da página e a página (lista nas linhas 4-24, linha 25 vazia, página na 26).
- A barra com o nome do arquivo ficou com **1 linha** (a 27): o nome mostra até 38 letras numa linha só, em vez de quebrar em duas.

### 1.17 — 2026-10-19
- **Rodapé da lista de jogos**: "Pág. x de y" em dourado e a barra com o nome do arquivo no vermelho do banner (antes cinza), com o nome em branco por cima.

### 1.16 — 2026-10-19
- **Correção: tela preta ao ligar nas versões 1.14 e 1.15.** O código novo do boot (que prepara a memória de vídeo para o wallpaper) zerava uma tabela usando `clr.w` na porta de dados do VDP. No 68000 essa instrução lê a porta antes de escrever, e ler a porta de dados com o VDP em modo de escrita trava o console de verdade (o emulador não acusava). Trocado por `move`; o build agora recusa esse tipo de instrução nas portas do VDP e o emulador de testes acusa a leitura.
- O boot também desliga a janela do VDP explicitamente.

### 1.15 — 2026-10-19
- Sem mudanças de código; só a versão (mesma numeração da v1).

### 1.14 — 2026-10-19
- **Wallpaper**: `/EDMD/WALL.ART` (320×224, até 14 cores, gerado com `make_wallpaper.py`) atrás da
  lista de jogos e dos menus. Mesmo arquivo para v1 e v3.
- Banner e wallpaper retrô próprios (livres para compartilhar) em `sd/EDMD`, gerados por `arte/gen_arte.py`.
- No boot, as tabelas de vídeo (janela, sprites, rolagem horizontal) ficam em 0xB000-0xBFFF, como na
  v1, para liberar a VRAM do wallpaper.

### 1.13 — 2026-10-19
- **Jogar com Cheats** no menu do arquivo (botão A): carrega o jogo, abre o editor de cheats
  (GG/RAW; *Aplicar* grava os códigos no jogo carregado) e, ao sair dele, inicia o jogo.
- Uma linha a mais entre o banner e o nome do jogo (menu do arquivo) e na tela Info da ROM.
- **Overlay**: Info da ROM, Opções, Recentes/Favoritos, Créditos e Jogar com Cheats agora ficam no
  próprio `MDOS.BIN`, depois dos 32 KB que a BIOS carrega, e são lidos do SD quando abertos. Isso
  liberou ~1,4 KB no OS para recursos novos. O arquivo precisa estar em `/EDMD/MDOS.BIN`; sem ele,
  essas telas não abrem (o resto funciona).

### 1.12 — 2026-10-18
- **Espaço entre o banner e a lista de jogos**: uma linha em branco embaixo do banner. A lista
  ocupa as linhas 4-24, a página fica na 25 e a barra com o nome do arquivo nas linhas 26-27.
- A capa da pré-visualização desceu uma linha para continuar no meio da lista.

### 1.11 — 2026-10-18
- **[ LIMPAR RECENTES ]** ganhou uma faixa vermelha atrás da linha, na largura da caixa do menu.
- Menu do arquivo: a capa fica direto na tela, sem a caixa "Boxart" (igual à v1); isso abriu o
  espaço para a faixa.

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
