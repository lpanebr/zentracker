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
- comando `add` para métricas arbitrárias;
- comando `table` para consulta tabular por período;
- comando `metrics` para listar métricas com dados;
- tipos por arquivo: `text`, `number`, `integer` e `bool`;
- persistência em arquivos texto, um por métrica;
- regra de "última entrada do dia" aplicada na leitura;
- testes automatizados com `unittest`;
- console scripts instaláveis: `zt` e `zentracker`;
- wrapper `./zt` apenas para desenvolvimento local sem instalação.

## Direção recomendada

Continuar evoluindo a CLI mínima antes de pensar em interface, banco ou sincronização.

Escopo decidido para a primeira versão:

1. Permitir métricas arbitrárias com nomes seguros.
2. Usar um arquivo separado por métrica.
3. Guardar o tipo da métrica no header opcional `# type:<tipo>`.
4. Resolver conflitos de múltiplas entradas no mesmo dia usando a última entrada na leitura.
5. Tratar ausência de dado como `nao informado`.

## Decisões registradas

```txt
zt add peso 92.4 --type number --date 2026-06-23
zt add academia sim --type bool --date 2026-06-23
zt add humor "bem disposto" --date 2026-06-23
zt table --from 2026-06-01 --to 2026-06-30 --metrics peso,academia,humor
```

- sem `--type`, métricas novas são `text`;
- arquivos antigos sem header são lidos como `text`;
- sem `--date`, o comando usa a data atual.
- múltiplas entradas no mesmo dia são preservadas no arquivo, mas a consulta considera a última.
- ausência de entrada para um dia significa `nao informado`.
- a saída principal da V1 é uma tabela simples por dia, com mais de uma métrica no mesmo período.
- o projeto não deve depender de configuração por usuário para funcionar como app.

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

- `python -m unittest discover -s tests` passou com 11 testes.
- fluxo manual validado com métricas `number`, `bool` e `text`.

## Pendências reais

1. Decidir se os dados fake em `data/` devem continuar versionados.
2. Melhorar a experiência de instalação neste ambiente local, que atualmente não tem `setuptools` importável.

## Observações sobre ambiente

- `mise` foi configurado globalmente com `python 3.12.13`.
- `python --version` e `python -m pip --version` passaram a funcionar.
- a instalação editável do pacote falha neste ambiente porque `setuptools` não está instalado.
- em ambientes Python normais, `pyproject.toml` expõe os comandos `zt` e `zentracker`.
- `./zt` continua útil para desenvolvimento local, mas não contém mais diretórios pessoais.

## Próximos passos sugeridos

1. Instalar `setuptools` no Python local ou usar um ambiente Python que já tenha backend de build.
2. Rodar `python -m pip install -e .` e validar `zt --help` fora do repositório.
3. Após validar o fluxo real, começar a pensar na próxima funcionalidade pequena:
   - resumo simples por período
   - ingestão via agente a partir de linguagem natural estruturada

## Restrições desejadas

- local-first;
- sem nuvem;
- sem banco de dados no início;
- sem dependências pesadas;
- tudo fácil de inspecionar no Git e no terminal.
