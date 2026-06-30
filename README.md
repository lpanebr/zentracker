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
- foco inicial em `peso` e `academia`;
- um arquivo por métrica;
- múltiplas entradas no mesmo dia são permitidas, mas a consulta usa a última;
- ausência de dado aparece como `-` na tabela.

## Uso

Fluxo recomendado neste ambiente, sem instalar nada:

```bash
./zt add peso 92.4 --date 2026-06-23
./zt add academia sim --date 2026-06-23
./zt metrics
./zt table --from 2026-06-20 --to 2026-06-22 --metrics peso,academia
```

O arquivo `./zt` é só um atalho que executa:

```bash
python -m zentracker --data-dir /home/lpanebr/Dropbox/brain-vaults/journaling/zentracker ...
```

Isso evita depender de `pip install` durante o desenvolvimento local e já separa o código dos dados.

Sem instalar:

```bash
python -m zentracker add peso 92.4 --date 2026-06-23
python -m zentracker add academia sim --date 2026-06-23
python -m zentracker metrics
python -m zentracker table --from 2026-06-20 --to 2026-06-22 --metrics peso,academia
```

Com instalação local do pacote:

```bash
python -m pip install -e .
zentracker add peso 92.4
zentracker add academia nao
```

Para deixar o comando acessível globalmente no seu usuário:

```bash
python -m pip install --user -e .
```

Depois confirme onde o executável foi criado:

```bash
which zentracker
```

Se o comando não for encontrado, provavelmente `~/.local/bin` ainda não está no seu `PATH`.

Observação: neste ambiente, a instalação com `pip` pode falhar se faltarem dependências locais de empacotamento ou se não houver acesso à internet para baixá-las. Por isso, `./zt` é o caminho mais confiável para usar a ferramenta agora.

## Formato de dados

Quando você usa `./zt`, os arquivos são salvos por métrica em:

```txt
/home/lpanebr/Dropbox/brain-vaults/journaling/zentracker
```

Exemplo:

```txt
/home/lpanebr/Dropbox/brain-vaults/journaling/zentracker/peso.txt
/home/lpanebr/Dropbox/brain-vaults/journaling/zentracker/academia.txt
```

Se você rodar `python -m zentracker` diretamente sem `--data-dir`, o padrão continua sendo `data/` dentro do repositório.

Cada linha guarda `data valor`:

```txt
2026-06-23 92.4
2026-06-23 sim
```

## Exemplo de saída

Listando métricas que já têm dados:

```txt
academia
peso
```

Tabela por período:

```txt
data        peso  academia
2026-06-20  92.4  sim
2026-06-21  92.1  nao
2026-06-22  -     sim
```

## Próximos passos

- ampliar cobertura de testes;
- permitir novas métricas sem quebrar a CLI;
- preparar a integração com agentes que convertam linguagem natural em comandos estruturados.
