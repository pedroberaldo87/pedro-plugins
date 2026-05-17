# Principles Index

Índice leve para roteamento de categorias. Lido pela skill /principles como primeiro passo — permite filtrar categorias relevantes sem carregar o documento completo (~1600 linhas).

## Documento Fonte

`/Users/pedroberaldo/Library/Mobile Documents/iCloud~md~obsidian/Documents/ObsidianPedro/DEV/PRINCIPIOS SISTEMAS.md`

## Mapa de Categorias

### 1 · Garantias transacionais (ACID e extensões)
**Trigger:** Sistema escreve dados que precisam sobreviver a falha. Múltiplas operações precisam ter sucesso/falhar juntas. Operações financeiras ou de inventário. Escritas concorrentes em estado compartilhado.
**Princípios:** Atomicidade, Consistência, Isolamento, Durabilidade, Linearizability, Serializability, Read-your-writes, Monotonic reads

### 2 · Idempotência e semântica de entrega
**Trigger:** Endpoints de API que criam/mutam. Consumidores de fila. Handlers de webhook. Lógica de retry. Processamento de pagamento. Envio de email/notificação.
**Princípios:** Idempotência, Reentrância, Determinismo, Semântica de entrega, Retry seguro, Deduplicação, Chaves de idempotência (com TTL), Resiliência a duplicidade/atraso/perda

### 3 · Concorrência, locking e ordering
**Trigger:** Múltiplos usuários/processos escrevendo no mesmo recurso. Locks distribuídos. Ordenação de eventos importa. Operações de contador/inventário.
**Princípios:** Concorrência segura e controle de corrida, Locking optimistic vs pessimistic, Compare-and-swap (CAS), Prevenção de deadlocks, Fencing tokens, Leases, Vector clocks e Lamport timestamps, Clock skew

### 4 · Tolerância a falha e resiliência
**Trigger:** Sistema com dependências externas (APIs, bancos, filas). Serviço que precisa funcionar quando partes falham. Alta disponibilidade é requisito. Operações que não podem perder dados.
**Princípios:** Tolerância a falhas e recuperabilidade, Timeout em tudo, Retry com backoff exponencial e jitter, Circuit breaker, Bulkhead, Backpressure e rate limiting, Fail-fast, Graceful degradation, Dead letter queue (DLQ), Connection pooling, Cold start awareness

### 5 · Sistemas distribuídos
**Trigger:** Mais de uma instância/nó/serviço. Replicação de dados. Comunicação entre serviços. Trade-offs de consistência. Transações que cruzam boundaries de serviço.
**Princípios:** CAP theorem, PACELC, Quorum (R + W > N), Consistência forte vs eventual, Saga pattern, Outbox + Inbox pattern, Event sourcing, CRDTs, Tail latency amplification

### 6 · Estado e dados
**Trigger:** Modelagem de dados. Decisões de cache. Escolha entre mutação vs imutabilidade. Definição de source of truth. Armazenamento persistente vs em memória.
**Princípios:** Imutabilidade quando possível, Single source of truth, Persistência explícita vs estado em memória, Statelessness quando possível, Normalização vs desnormalização controlada, Cache com invalidação clara, Reversibilidade

### 7 · Evolução e mudança
**Trigger:** APIs que terão múltiplas versões. Schema de banco que vai mudar. Deploys sem downtime. Clientes em versões diferentes. Feature rollout gradual.
**Princípios:** Versionamento, Backwards vs forwards compatibility, Schema evolution, Migrações seguras (expand→migrate→contract), Feature flags, Deploy seguro (canário/blue-green/rolling), Rollback possível

### 8 · Observabilidade
**Trigger:** Sistema em produção que precisa ser monitorado. Debug de problemas em microserviços. Definição de SLOs. Alertas. Necessidade de entender o que aconteceu quando algo deu errado.
**Princípios:** Os três pilares (logs, métricas, traces), Logs estruturados, Métricas com percentis, Distributed tracing, Health checks (liveness ≠ readiness), SLO/SLA/error budget, Alertas acionáveis, Replayability e reprodutibilidade

### 9 · Segurança e governança
**Trigger:** Autenticação/autorização. Dados sensíveis. APIs públicas. Compliance (LGPD, HIPAA, SOC2). Credenciais e secrets. Input de usuário.
**Princípios:** Autenticação vs autorização, Privilégio mínimo, Encryption in transit + at rest, Secret rotation, Validação de entrada vs sanitização, Auditabilidade e audit log, Segurança por padrão e privacidade por design

### 10 · Design de software
**Trigger:** Arquitetura de módulos/serviços. Definição de interfaces. Modelagem de domínio. Decisões de acoplamento. Contratos entre componentes.
**Princípios:** Separação de responsabilidades/baixo acoplamento/alta coesão, Contratos explícitos, Limites entre domínios (DDD), Modelagem correta de invariantes, Boundaries de consistência explícitas, Evitar efeitos colaterais ocultos, Configuração externa ao código (12-factor), Testabilidade, Documentação dos contratos críticos

### 11 · Escala
**Trigger:** Volume de dados ou tráfego cresce. Necessidade de múltiplas instâncias. Particionamento de dados. Performance sob carga.
**Princípios:** Escalabilidade horizontal, Sharding/particionamento

### 12 · Resiliência de rede e service discovery
**Trigger:** Comunicação entre serviços. DNS envolvido em roteamento. Descoberta de serviços dinâmica. Ambiente com containers/orquestração. Rede entre datacenters.
**Princípios:** DNS caching e TTL, Service discovery, Service mesh, Health-aware routing, Partições de rede além do CAP

### 13 · Gerenciamento de dependências e supply chain
**Trigger:** Projeto com dependências externas (npm, pip, cargo). Build precisa ser reprodutível. Auditoria de segurança de deps. Monorepo com deps compartilhadas.
**Princípios:** Lock files e pinning, Reproducible builds, Supply chain security, Dependency hygiene, Vendoring vs registry

### 14 · Concorrência na camada de aplicação
**Trigger:** Código async/await. Thread pools. Workers concorrentes. Canais/filas internas. Processamento paralelo na aplicação. Event loop.
**Princípios:** Shared mutable state vs message passing, Async/await pitfalls, Thread pools e work stealing, Actor model, Structured concurrency, Backpressure na aplicação

### 15 · Testes como garantia de sistema
**Trigger:** Múltiplos serviços com contratos entre si. Sistema que precisa ser resiliente sob falha. Capacidade desconhecida. Deploy frequente em produção.
**Princípios:** Contract testing, Chaos testing, Load testing e capacity planning, Property-based testing, Smoke tests em produção, Test pyramid vs trophy

### 16 · Data lifecycle e compliance
**Trigger:** Dados pessoais (PII). Requisitos LGPD/GDPR. Ambientes de teste com dados reais. Retenção de dados. Dados cruzando fronteiras geográficas.
**Princípios:** Classificação de dados, Retenção e expurgação, Right to be forgotten, Data masking, Anonimização vs pseudonimização, Cross-border data

### 17 · Operações e resposta a incidentes
**Trigger:** Sistema em produção com SLA. Equipe de on-call. Processos de resposta a incidentes. Necessidade de runbooks. Post-mortems.
**Princípios:** Runbooks como artefato de engenharia, Incident response lifecycle, Postmortem blameless, On-call design, Comunicação durante incidente, War rooms

### 18 · API design patterns
**Trigger:** Projetando API REST/GraphQL. Endpoints de listagem com muitos resultados. Operações em lote. Notificações assíncronas para consumidores. Gateway centralizado.
**Princípios:** Pagination (cursor vs offset), Bulk operations, Webhooks e event subscriptions, Rate limiting do lado consumidor, API gateways, Hypermedia e discoverability, Content negotiation e evolução

### 19 · Infraestrutura como código
**Trigger:** Provisionamento de servidores/containers. Configuração de infra. Ambientes precisam ser replicáveis. Deploy de infra. Secrets em pipelines de CI/CD.
**Princípios:** IaC princípios, Immutable infrastructure, GitOps, Drift detection, Environment parity, Secrets management em IaC
