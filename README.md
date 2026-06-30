# zentracker

Aplicativo local e simples para rastrear coisas aleatórias da vida em arquivos de texto, com sintaxe leve, grepável e inspirada no `todo.txt`.

O foco do `zentracker` não é gerenciar tarefas, mas registrar eventos, contagens, estados, medições, observações e pequenos fatos do dia a dia sem depender de banco de dados, interface pesada ou nuvem.

## Ideia

O projeto nasce da vontade de ter um formato tão simples quanto um arquivo `.txt`, mas mais flexível para acompanhar coisas como:

- hábitos e rotinas;
- humor, energia, sono e peso;
- sintomas, remédios e medições;
- estudos, treinos e leituras;
- gastos rápidos ou contagens diversas;
- qualquer coisa que valha a pena registrar sem criar atrito.

## Princípios

- local-first;
- arquivos de texto simples;
- formato legível sem ferramenta;
- dados fáceis de buscar com `rg`, `awk` e afins;
- baixo atrito para registrar;
- fácil de versionar no Git;
- sem dependências grandes desnecessárias.

## Exemplo de uso

```txt
2026-06-23 cafe +energia nota:me deixou mais ligado
2026-06-23 treino caminhada duracao:30min +saude
2026-06-23 humor 8/10 +estado
2026-06-23 peso 92.4kg +saude
2026-06-23 artur trabalho-cafe status:conversa +familia
```

## Objetivo inicial

Ter uma primeira versão capaz de:

- registrar entradas em arquivos texto;
- consultar histórico por período;
- manter um formato consistente e humano;
- permitir automações simples em shell ou Python.

## Escopo atual da V1

- CLI estruturada em Python;
- métricas arbitrárias com nomes seguros;
- tipos iniciais: `text`, `number`, `integer` e `bool`;
- um arquivo por métrica;
- múltiplas entradas no mesmo dia são permitidas, mas a consulta usa a última;
- ausência de dado aparece como `-` na tabela.

## Uso

Instale localmente no ambiente Python atual:

```bash
python -m pip install -e .
```

Se o Python gerenciado por `mise` não tiver `setuptools`, instale o backend uma vez e use o ambiente atual sem isolamento de build:

```bash
python -m pip install setuptools
python -m pip install -e . --no-build-isolation
```

Isso instala dois comandos equivalentes:

```bash
zt
zentracker
```

Fluxo básico:

```bash
zt add peso 92.4 --type number --date 2026-06-23
zt add academia sim --type bool --date 2026-06-23
zt add humor "bem disposto" --date 2026-06-23
zt metrics
zt table --from 2026-06-20 --to 2026-06-22 --metrics peso,academia,humor
```

Sem instalar, para desenvolvimento:

```bash
python -m zentracker add peso 92.4 --type number
./zt add peso 92.4 --type number
```

Para instalar só no usuário:

```bash
python -m pip install --user -e .
```

Depois confirme onde o executável foi criado:

```bash
which zt
```

Se o comando não for encontrado, provavelmente `~/.local/bin` ainda não está no seu `PATH`.

## Formato de dados

Por padrão, os arquivos são salvos em:

```txt
~/.local/share/zentracker
```

Se `XDG_DATA_HOME` estiver definido, o padrão vira:

```txt
$XDG_DATA_HOME/zentracker
```

Você também pode sobrescrever o diretório com `ZENTRACKER_DATA_DIR`:

```bash
export ZENTRACKER_DATA_DIR="$HOME/Dropbox/zentracker"
```

Ou por comando:

```bash
zt --data-dir "$HOME/Dropbox/zentracker" metrics
```

Exemplo de arquivos:

```txt
~/.local/share/zentracker/peso.txt
~/.local/share/zentracker/academia.txt
```

Cada linha guarda `data valor`:

```txt
# type:number
2026-06-23 92.4
```

A primeira linha pode declarar o tipo da métrica:

```txt
# type:text
# type:number
# type:integer
# type:bool
```

Se um arquivo antigo não tiver essa linha, o tipo assumido é `text`.

Valores aceitos por tipo:

- `text`: qualquer texto não vazio;
- `number`: número decimal;
- `integer`: número inteiro;
- `bool`: `sim`/`nao`, `true`/`false` ou `1`/`0`, salvo como `sim` ou `nao`.

Exemplo de booleano:

```txt
# type:bool
2026-06-23 sim
```

## Exemplo de saída

Listando métricas que já têm dados:

```txt
academia
humor
peso
```

Tabela por período:

```txt
data        peso  academia  humor
2026-06-20  92.4  sim       -
2026-06-21  92.1  nao       bem disposto
2026-06-22  -     sim       cansado
```

## Próximos passos

- ampliar cobertura de testes;
- preparar a integração com agentes que convertam linguagem natural em comandos estruturados.
