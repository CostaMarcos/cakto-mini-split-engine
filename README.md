# Cakto mini split payment engine

### Etapas de desenvolvimento

O desenvolvimento foi dividido em etapas para manter o foco na lógica de negócio e na confiabilidade:

#### Cotação | Cálculo de split (core) [PR relacionado](https://github.com/CostaMarcos/cakto-mini-split-engine/pull/1)
  - Utilizei o `Decimal` do Python para evitar problemas de ponto flutuante e garantir precisão exata.
  - Para arredondamento usei `ROUND_HALF_UP` com precisão de `0.01`. Valores com mais de duas casas decimais são arredondados corretamente, e o último recebedor do split fica com saldo restante. Isso assegura que a soma dos valores distribuídos seja igual ao total da transação.

- Endpoint implementado: `/checkout/quote`
- Testes:
  - Testes unitários para lógica de cálculo e regras de distribuição
  - Testes de integração usando `django-tests` para validar o fluxo completo

#### Endpoint de pagamento (MVP) [PR relacionado](https://github.com/CostaMarcos/cakto-mini-split-engine/pull/2)
- Defini as tabelas no banco de dados: `Payment`, `LedgerEntry`, `OutboxEvent`.
- Implementei o endpoint REST: `/payments`.
- Desenvolvi a integração do fluxo com a lógica de split do core, gravando os resultados em banco após o cálculo da transferência. Nesta fase, não implementei a arquitetura de eventos, para validar rapidamente o caminho de pagamento.

#### Endpoint de Eventos [PR Relacionado](https://github.com/CostaMarcos/cakto-mini-split-engine/pull/3)

- Integrei RabbitMQ e Celery para realizar processamento assíncrono de pagamentos. Com isso, a API responde rápido ao usuário enquanto o trabalho de confirmação e liquidação é processado em background.
- Adicionei cache de idempotência para detectar pagamentos já realizados ou em processamento, evitando duplicidades e reprocessamentos desnecessários.
- Ampliei a base de testes (unitários e de integração) para garantir estabilidade e prevenir regressões ao modificar a lógica de negócio.

#### Pontos de melhoria

- Implementar um tratamento de falhas mais sofisticado no fluxo de processamento, com um serviço dedicado a pagamentos com erro e políticas de retries/exponential backoff, para evitar repetidas falhas com o mesmo payload.
- Adicionar observabilidade na plataforma (logs estruturados, métricas e tracing distribuído), facilitando a detecção, correlação e diagnóstico de erros.
- Avaliar execução de processamento em ambientes serverless (funções Lambda ou similares) para reduzir impacto de pico de transações no servidor principal.
- Substituir o cache de desenvolvimento por uma solução de cache de produção (Redis, Memcached ou equivalente) para diminuir leituras no banco e melhorar desempenho em alta carga.
- Parametrizar as regras de taxa e divisão de receita para permitir ajustes por interface ou API, sem necessidade de deploy de código.

#### Utilização de IA

- Utilizei IA principalmente para acelerar a criação de boilerplate, incluindo a configuração inicial do projeto Django, Dockerfile, docker-compose.yml e outros arquivos padrão.
- Gerei casos de teste básicos e edge cases com IA, complementando com testes manuais específicos para validar a lógica de negócio.
- Aproveitei o autocomplete e consultas à IA para pesquisar e implementar boas práticas do setor financeiro, garantindo conformidade e segurança.

###  Como Executar o Projeto

Antes de executar o projeto, você precisa configurar as variáveis de ambiente:

1. **Copie o arquivo de exemplo:**
   ```bash
   cp .env.example .env
   ```

2. **Remova o `.example` do nome do arquivo** (o comando acima já faz isso, mas se precisar manualmente):
   ```bash
   mv .env.example .env
   ```

### Executando com Docker

1. **Inicie os containers:**
   ```bash
   docker compose up -d
   ```

2. **Execute as migrações do banco de dados:**
   ```bash
   docker compose exec backend python manage.py migrate
   ```

3. **Acesse a aplicação:**
   - A aplicação estará disponível em `http://localhost:8888`
