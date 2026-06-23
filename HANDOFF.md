# Handoff

## Contexto

Projeto pessoal de Luciano Panepucci em:

`/home/lpanebr/Dropbox/github/lpanebr/zentracker`

A ideia do projeto é criar um aplicativo local, simples e grepável para rastrear coisas aleatórias da vida usando arquivos de texto, inspirado no `todo.txt`, mas focado em registros e não em tarefas.

Já existe um `README.md` inicial com a visão do projeto.

## Estado atual

A base da V1 já foi implementada e testada localmente dentro do repositório.

O que existe hoje:

- CLI em Python no pacote `zentracker/`;
- comando `add` para `peso` e `academia`;
- comando `table` para consulta tabular por período;
- persistência em arquivos texto, um por métrica;
- regra de "última entrada do dia" aplicada na leitura;
- testes automatizados com `unittest`;
- script wrapper `./zt` para uso sem instalação via `pip`.

## Direção recomendada

Continuar evoluindo a CLI mínima antes de pensar em interface, banco ou sincronização.

Escopo decidido para a primeira versão:

1. Focar inicialmente em duas métricas: `peso` e `academia`.
2. Usar um arquivo separado por métrica.
3. Implementar comandos estruturados de `add` e consulta tabular por período.
4. Resolver conflitos de múltiplas entradas no mesmo dia usando a última entrada na leitura.
5. Tratar ausência de dado como `nao informado`.

## Decisões registradas

```txt
./zt add peso 92.4 --date 2026-06-23
./zt add academia sim --date 2026-06-23
./zt table --from 2026-06-01 --to 2026-06-30 --metrics peso,academia
```

- `peso` armazena apenas um valor numérico.
- `academia` armazena `sim` ou `nao`.
- sem `--date`, o comando usa a data atual.
- múltiplas entradas no mesmo dia são preservadas no arquivo, mas a consulta considera a última.
- ausência de entrada para um dia não significa `nao`; significa `nao informado`.
- `academia` deve ser registrada explicitamente, inclusive para `nao`.
- a saída principal da V1 é uma tabela simples por dia, com mais de uma métrica no mesmo período.
- o projeto deve permanecer genérico o suficiente para novas métricas, sem introduzir arquitetura pesada cedo demais.

## Referência principal

A especificação detalhada e o plano de implementação da V1 estão em `SPEC.md`.

## Implementado nesta sessão

1. Inicialização do repositório Git.
2. Criação de `SPEC.md` com escopo e plano da V1.
3. Implementação do pacote `zentracker` com:
   - `add`
   - `table`
   - validação de métricas
   - persistência em texto
4. Adição de testes em `tests/test_cli.py`.
5. Criação de dados fake de uma semana em `data/peso.txt` e `data/academia.txt`.
6. Criação do wrapper `./zt`.
7. Atualização do `README.md` com instruções de uso.

## Validação executada

- `python -m unittest discover -s tests -v` passou com 4 testes.
- `./zt table --from 2026-06-16 --to 2026-06-22 --metrics peso,academia` funcionou usando os dados fake do repositório.

## Pendências reais

1. Decidir se o wrapper final deve continuar como `./zt` no repositório ou se também deve existir um atalho em `~/.local/bin`.
2. Validar o uso do diretório de dados no Dropbox fora do sandbox:
   - caminho desejado: `/home/lpanebr/Dropbox/brain-vaults/journaling/zentracker`
   - o script `./zt` já foi ajustado para isso
   - a validação automática falhou por limitação de escrita do sandbox, não por bug confirmado do projeto
3. Decidir se os dados fake em `data/` devem continuar versionados ou se devem ser removidos depois que o diretório real no Dropbox estiver em uso.
4. Melhorar a experiência de instalação, caso ainda faça sentido, porque o ambiente com `mise` ficou com `python` e `pip` resolvidos, mas `pip install -e .` não funcionou por falta de `setuptools` disponível offline.

## Observações sobre ambiente

- `mise` foi configurado globalmente com `python 3.12.13`.
- `python --version` e `python -m pip --version` passaram a funcionar.
- a instalação editável do pacote continua pendente por limitação de dependências de empacotamento fora da rede.
- por enquanto, o caminho mais confiável para uso é `./zt`.

## Próximos passos sugeridos

1. Testar manualmente `./zt` no shell do usuário, já apontando para o diretório real no Dropbox journaling.
2. Se a ideia for usar de qualquer lugar no terminal, criar depois um atalho simples em `~/.local/bin/zt` apontando para este repositório.
3. Após validar o fluxo real, começar a pensar na próxima funcionalidade pequena:
   - resumo simples por período
   - suporte a nova métrica
   - ingestão via agente a partir de linguagem natural estruturada

## Restrições desejadas

- local-first;
- sem nuvem;
- sem banco de dados no início;
- sem dependências pesadas;
- tudo fácil de inspecionar no Git e no terminal.
