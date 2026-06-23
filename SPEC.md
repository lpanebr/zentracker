# Especificação V1

## Objetivo

Construir uma CLI local-first para registrar e consultar métricas pessoais simples em arquivos texto, com foco em baixo atrito, legibilidade e futura integração com agentes que transformem linguagem natural em comandos estruturados.

## Escopo inicial

A V1 cobre apenas duas métricas:

- `peso`
- `academia`

O desenho deve permitir adicionar novas métricas depois sem reescrever a base, mas sem criar uma arquitetura genérica demais agora.

## Princípios

- uso via linha de comando;
- dados em arquivos de texto simples;
- um arquivo por métrica;
- sem banco de dados;
- sem dependências pesadas;
- fácil de automatizar via shell, Python ou agente de IA.

## Modelo de dados

### Métrica `peso`

- valor numérico simples;
- um registro representa o peso de uma data;
- se houver múltiplos registros no mesmo dia, vale o último na consulta.

### Métrica `academia`

- valor binário explícito;
- valores aceitos: `sim` e `nao`;
- ausência de registro não significa `nao`; significa `nao informado`;
- se houver múltiplos registros no mesmo dia, vale o último na consulta.

## Armazenamento

Cada métrica fica em seu próprio arquivo texto dentro de um diretório de dados.

Sugestão inicial:

```txt
data/peso.txt
data/academia.txt
```

Formato de linha sugerido para a V1:

```txt
2026-06-23 92.4
2026-06-23 sim
```

Regras:

- a data vem em ISO `YYYY-MM-DD`;
- o valor vem após um espaço;
- o arquivo pode conter múltiplas linhas para a mesma data;
- a resolução de conflito acontece na leitura, escolhendo a última linha da data.

## Interface de linha de comando

### Registro

Comandos iniciais:

```bash
zentracker add peso 92.4 --date 2026-06-23
zentracker add academia sim --date 2026-06-23
```

Regras:

- `--date` é opcional;
- sem `--date`, usar a data atual;
- `peso` deve validar entrada numérica;
- `academia` deve validar `sim` ou `nao`.

### Consulta tabular

Comando inicial:

```bash
zentracker table --from 2026-06-01 --to 2026-06-30 --metrics peso,academia
```

Saída esperada:

```txt
data        peso    academia
2026-06-20  92.4    sim
2026-06-21  92.1    nao
2026-06-22  -       sim
```

Regras:

- listar um dia por linha dentro do intervalo;
- permitir combinar mais de uma métrica na mesma tabela;
- preencher ausência com `-`;
- ao montar a tabela, usar a última entrada encontrada no dia para cada métrica.

## Casos de uso da V1

1. Registrar o peso do dia.
2. Registrar explicitamente se foi ou não à academia.
3. Consultar um intervalo de datas com uma única métrica.
4. Consultar um intervalo de datas combinando `peso` e `academia`.
5. Preparar o caminho para um agente gerar esses mesmos comandos a partir de texto livre.

## Decisões importantes

### Múltiplas entradas no mesmo dia

- serão permitidas no arquivo;
- a consulta usará a última entrada do dia;
- isso preserva histórico bruto e evita reescrita de arquivo.

### Dados ausentes

- um dia sem linha para uma métrica é `nao informado`;
- isso é diferente de `academia nao`.

### Linguagem natural

- não faz parte da V1;
- a V1 deve expor comandos estruturados simples para que um agente possa chamá-los depois.

## Fora de escopo na V1

- interface gráfica;
- sincronização;
- banco de dados;
- dashboards;
- estatísticas avançadas;
- parsing nativo de linguagem natural;
- edição interativa de registros antigos.

## Plano de implementação

1. Criar a estrutura inicial em Python.
2. Definir o pacote e o ponto de entrada da CLI.
3. Criar o diretório `data/` e a camada mínima de persistência por métrica.
4. Implementar `add` com validação para `peso` e `academia`.
5. Implementar leitura por período com resolução de "última entrada do dia".
6. Implementar `table` com múltiplas métricas e preenchimento de ausências com `-`.
7. Adicionar testes para parsing, validação, conflito no mesmo dia e geração da tabela.
8. Atualizar o README com exemplos reais de uso da V1.

## Critério de sucesso da V1

A V1 está pronta quando for possível:

- registrar `peso` e `academia` rapidamente no terminal;
- consultar um período em formato tabular;
- combinar ambas as métricas na mesma saída;
- lidar corretamente com dias ausentes e múltiplos registros no mesmo dia.
