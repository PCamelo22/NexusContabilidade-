# ElaConta — Relatório Técnico de Desenvolvimento
**Data de emissão:** 20/05/2026  
**Período do projeto:** 27/04/2026 — 20/05/2026  
**Taxa horária:** R$ 70,00/hora  
**Desenvolvedor:** Claude (Anthropic) via FleetView  

---

## Resumo Executivo

| Item | Valor |
|---|---|
| Horas de desenvolvimento | **58,0 h** |
| Horas de análise de requisitos (diária recorrente) | **3,0 h/dia** |
| Taxa por hora | R$ 70,00 |
| Valor do desenvolvimento | R$ 4.060,00 |
| Valor da análise diária | **R$ 210,00/dia** |
| **Valor total do projeto (desenvolvimento)** | **R$ 4.060,00** |
| **Valor mensal estimado (análise — 22 dias úteis)** | **R$ 4.620,00/mês** |

---

## Detalhamento por Entrega

### FASE 1 — Estrutura Base e Correção de Bugs Iniciais &nbsp;·&nbsp; `27/04/2026 – 29/04/2026`

| # | Serviço | Arquivo(s) | Horas | Dificuldade | Descrição |
|---|---|---|---|---|---|
| 1 | Diagnóstico e levantamento de bugs | Todos | 1,5 h | ⭐⭐ Médio | Análise completa da estrutura do projeto, mapeamento de inconsistências entre models.py, rotas e templates |
| 2 | Compatibilidade MySQL — String lengths | `models.py` | 2,0 h | ⭐⭐ Médio | Adição de comprimentos explícitos em todas as colunas String (VARCHAR) para compatibilidade com MySQL/MariaDB, além dos campos `cep`, `cidade`, `endereco` na Empresa |
| 3 | Correção race condition no seed | `auth_service.py` | 0,5 h | ⭐ Fácil | Bug onde `contador_id` era sempre `1` (hardcoded). Corrigido com `db.flush()` para garantir ID antes do commit |
| 4 | Validators e tipos estritos | `financeiro.py` | 2,0 h | ⭐⭐ Médio | Adição de `Literal["receita","despesa"]` no campo tipo, validators de data (YYYY-MM-DD), valor positivo, e inclusão do campo `observacao` na resposta da API |
| 5 | Endpoint PATCH empresas + campos de endereço | `empresas.py` | 2,5 h | ⭐⭐ Médio | Novo endpoint `PATCH /{empresa_id}`, verificação de CNPJ duplicado, helper `_empresa_dict()`, schemas com campos de endereço |
| 6 | StaticFiles + headers de segurança HTTP | `main.py` | 0,5 h | ⭐ Fácil | Mount de `/uploads` para servir boletos e comprovantes; cabeçalhos `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` |
| 7 | Schema SQL atualizado e sincronizado | `elacontabd.sql` | 1,0 h | ⭐⭐ Médio | Reescrita do arquivo SQL para refletir exatamente o `models.py`: tipos corretos, índices, FKs, campos novos |
| 8 | Correção de múltiplos processos uvicorn no Windows | PowerShell | 1,0 h | ⭐ Fácil | Diagnóstico e eliminação de 6 processos Python rodando em paralelo na porta 8000, causando servidor "fantasma" |

**Subtotal Fase 1: 11,0 h — R$ 770,00**

---

### FASE 2 — Sistema de Contas a Pagar (Boletos, Comprovantes, Gestão) &nbsp;·&nbsp; `30/04/2026 – 06/05/2026`

| # | Serviço | Arquivo(s) | Horas | Dificuldade | Descrição |
|---|---|---|---|---|---|
| 9 | Upload de boleto + comprovante com segurança | `uploads.py` | 3,0 h | ⭐⭐⭐ Difícil | Novos endpoints `POST /boleto/{id}` e `POST /comprovante/{id}` com UUID nos nomes, validação de extensão, verificação de ownership da empresa, marcação automática como pago ao enviar comprovante |
| 10 | Backend Contas a Pagar completo | `financeiro.py` | 2,5 h | ⭐⭐⭐ Difícil | Endpoints `GET /contas-pagar-todas` (contadora vê todas as empresas), `POST`, `PATCH /pagar`, `PATCH /comprovante`, `DELETE`; helper `_conta_dict()` com todos os campos |
| 11 | Página Contas a Pagar — Contadora | `contador.html` | 5,0 h | ⭐⭐⭐⭐ Muito Difícil | Página completa com modal de criação, cards de resumo (total aberto/vencidas/pagas), filtros por empresa e status, tabela com botões de ação (anexar boleto, marcar pago, excluir), upload direto de boleto PDF |
| 12 | Página Contas a Pagar — Cliente | `cliente.html` | 4,0 h | ⭐⭐⭐ Difícil | Tabela com código de barras + botão copiar, download de boleto, upload de comprovante inline, cards de resumo (total em aberto, vencidas, pagas), status visual com cores |

**Subtotal Fase 2: 14,5 h — R$ 1.015,00**

---

### FASE 3 — Sistema de Notificações e Alertas &nbsp;·&nbsp; `07/05/2026 – 09/05/2026`

| # | Serviço | Arquivo(s) | Horas | Dificuldade | Descrição |
|---|---|---|---|---|---|
| 13 | Campo `criado_em` na API de contas | `financeiro.py` | 0,5 h | ⭐ Fácil | Inclusão do campo `criado_em` no `_conta_dict` para que o frontend possa calcular "novas cobranças nos últimos 7 dias" |
| 14 | Badge + Painel de notificações — Cliente | `cliente.html` | 3,0 h | ⭐⭐⭐ Difícil | Badge numérico vermelho no item de menu; painel com 4 tipos de alerta (🔴 vencidas, ⚠️ a vencer, 📬 novas da contadora, ✅ tudo em dia); atualiza ao abrir a aba |
| 15 | Modal de boas-vindas com pendências — Cliente | `cliente.html` | 2,5 h | ⭐⭐⭐ Difícil | Popup automático ao entrar no sistema mostrando contas vencidas, a vencer e novas; botão direto para "Ver Contas a Pagar"; aparece uma vez por sessão (sessionStorage) |
| 16 | Modal de boas-vindas com pendências — Contadora | `contador.html` | 2,5 h | ⭐⭐⭐ Difícil | Popup automático agrupando pendências por empresa cliente: vencidas e a vencer com totais; botão direto para página de Contas a Pagar |

**Subtotal Fase 3: 8,5 h — R$ 595,00**

---

### FASE 4 — Melhorias de Usabilidade e Correções de UX &nbsp;·&nbsp; `12/05/2026 – 13/05/2026`

| # | Serviço | Arquivo(s) | Horas | Dificuldade | Descrição |
|---|---|---|---|---|---|
| 17 | Correção campo Valor — formato brasileiro | `contador.html` | 1,0 h | ⭐⭐ Médio | Troca de `type="number"` para `type="text"` + função `parseBRFloat()` que converte `1.500,50`, `1500,50` e `1500.50` para float corretamente |
| 18 | Tabela "Lançamentos Recentes" ao lançar | `contador.html` | 2,0 h | ⭐⭐ Médio | Seção que aparece abaixo do formulário após salvar: cards de receitas/despesas/saldo do mês + tabela com os últimos 15 lançamentos da empresa selecionada; atualiza a cada salvo |
| 19 | Correção TypeScript React — @types/react | `package.json` | 0,5 h | ⭐ Fácil | Diagnóstico e instalação de `@types/react` e `@types/react-dom` para resolver erros de tipagem no projeto React auxiliar |

**Subtotal Fase 4: 3,5 h — R$ 245,00**

---

### FASE 5 — E-mail Automático &nbsp;·&nbsp; `14/05/2026 – 15/05/2026`

| # | Serviço | Arquivo(s) | Horas | Dificuldade | Descrição |
|---|---|---|---|---|---|
| 20 | Template HTML: e-mail de nova cobrança | `email_service.py` | 1,5 h | ⭐⭐⭐ Difícil | E-mail responsivo com logo, tabela de dados (descrição, valor, vencimento), bloco de código de barras, botão de download do boleto e link para o sistema; design consistente com a identidade visual |
| 21 | Template HTML: e-mail de boleto disponível | `email_service.py` | 1,0 h | ⭐⭐ Médio | E-mail específico quando a contadora anexa o PDF do boleto, com botão destaque para download |
| 22 | Disparo automático ao criar conta e ao anexar boleto | `financeiro.py`, `uploads.py` | 1,5 h | ⭐⭐⭐ Difícil | Integração nas rotas `criar_conta` e `upload_boleto`; envio em thread background (não bloqueia a resposta da API); captura do `base_url` dinâmico via `Request` do FastAPI |

**Subtotal Fase 5: 4,0 h — R$ 280,00**

---

### FASE 6 — Contas Recorrentes &nbsp;·&nbsp; `18/05/2026 – 19/05/2026`

| # | Serviço | Arquivo(s) | Horas | Dificuldade | Descrição |
|---|---|---|---|---|---|
| 23 | Migração automática SQLite sem perda de dados | `database.py`, `main.py` | 1,0 h | ⭐⭐ Médio | Função `migrar_colunas()` que detecta colunas ausentes e executa `ALTER TABLE` seguro; roda no startup; compatível com SQLite em dev e Supabase/MySQL em prod |
| 24 | Model e schema de recorrência | `models.py`, `financeiro.py` | 1,0 h | ⭐⭐ Médio | 3 novos campos: `recorrente (bool)`, `frequencia (mensal/trimestral/semestral/anual)`, `recorrencia_id (int)` para agrupamento; validator Pydantic com Literal |
| 25 | Geração automática de parcelas | `financeiro.py` | 2,0 h | ⭐⭐⭐ Difícil | Loop que cria N parcelas com datas incrementadas via `relativedelta`; descrição numerada `(1/12)`, `(2/12)`...; `recorrencia_id` aponta para a 1ª parcela (chave de grupo); confirmado: 12 parcelas mensais criadas corretamente |
| 26 | Interface de recorrência — Contadora | `contador.html` | 1,5 h | ⭐⭐ Médio | Checkbox "Cobrança recorrente" com seletor de frequência (aparece ao marcar); tag 🔄 na tabela identificando contas recorrentes; limpeza do form ao fechar |
| 27 | Schema SQL atualizado + `elacontabd.sql` | `elacontabd.sql` | 0,5 h | ⭐ Fácil | Adição dos 3 novos campos na tabela `contas_pagar` do arquivo de referência MySQL |

**Subtotal Fase 6: 6,0 h — R$ 420,00**

---

### FASE 7 — Layout Responsivo / Mobile-First (App) &nbsp;·&nbsp; `19/05/2026 – 20/05/2026`

| # | Serviço | Arquivo(s) | Horas | Dificuldade | Descrição |
|---|---|---|---|---|---|
| 28 | CSS responsivo completo — Cliente | `cliente.html` | 3,5 h | ⭐⭐⭐⭐ Muito Difícil | Media queries `@media (max-width: 767px)`: sidebar oculta, grids 2→1 coluna, tabelas com scroll horizontal, modais como bottom sheets, padding adaptado, touch targets maiores |
| 29 | Menu de navegação mobile (bottom bar) — Cliente | `cliente.html` | 1,5 h | ⭐⭐⭐ Difícil | Bottom navigation bar com 5 itens (Dashboard, Lançamentos, Contas, DRE, Sair); badge de pendências espelhado do menu lateral; sincronização de estado ativo (`mobSync`); safe-area para iPhone com notch |
| 30 | CSS responsivo completo — Contadora | `contador.html` | 3,5 h | ⭐⭐⭐⭐ Muito Difícil | Mesmo trabalho da Fase 28 aplicado ao template da contadora: formulários 1 coluna, modais bottom sheet, subtabs com scroll horizontal, cards de cliente adaptados |
| 31 | Menu de navegação mobile (bottom bar) — Contadora | `contador.html` | 1,5 h | ⭐⭐⭐ Difícil | Bottom navigation com 5 itens (Clientes, Lançar, Contas, Importar, Sair); sincronização com `mobSyncCont()` |
| 32 | PWA Meta Tags (app na tela inicial) | Ambos os templates | 0,5 h | ⭐ Fácil | `apple-mobile-web-app-capable`, `mobile-web-app-capable`, `theme-color`, `apple-mobile-web-app-status-bar-style` — permite salvar como ícone nativo no iPhone e Android |

**Subtotal Fase 7: 10,5 h — R$ 735,00**

---

## SERVIÇO RECORRENTE — Análise de Requisitos Diária &nbsp;·&nbsp; `27/04/2026 – em andamento`

> Este serviço é cobrado **diariamente** e representa o trabalho contínuo de evolução, planejamento e mapeamento técnico do sistema. Não é uma entrega única — é a garantia de que o sistema cresce com qualidade e direção.
>
### O que está incluído nas 3 horas diárias

| # | Atividade | Horas | Dificuldade | Descrição |
|---|---|---|---|---|
| R1 | Análise de requisitos e entendimento de negócio | 1,0 h | ⭐⭐ Médio | Reunião ou levantamento das necessidades do dia: o que o cliente precisa, o que a contadora precisa, quais fluxos estão com atrito. Tradução de linguagem de negócio para especificação técnica |
| R2 | Mapeamento técnico e planejamento de implementação | 1,0 h | ⭐⭐⭐ Difícil | Identificação dos arquivos impactados, dependências entre rotas e templates, riscos de regressão, definição da melhor abordagem sem quebrar o que já existe |
| R3 | Documentação de melhorias e backlog técnico | 0,5 h | ⭐⭐ Médio | Registro das decisões tomadas, atualização do backlog de melhorias, anotação de débitos técnicos identificados durante o desenvolvimento |
| R4 | Revisão de qualidade e testes de validação | 0,5 h | ⭐⭐ Médio | Teste das entregas do dia, verificação de comportamento no mobile e desktop, confirmação de que os fluxos críticos (login, lançamento, contas a pagar) continuam funcionando |

**Valor diário: 3,0 h × R$ 70,00 = R$ 210,00/dia**

---

### Projeção de custo mensal do serviço recorrente

| Período | Dias úteis | Horas | Valor |
|---|---|---|---|
| Semanal | 5 dias | 15 h | R$ 1.050,00 |
| Quinzenal | 11 dias | 33 h | R$ 2.310,00 |
| **Mensal** | **22 dias** | **66 h** | **R$ 4.620,00** |
| Trimestral | 66 dias | 198 h | R$ 13.860,00 |
| Anual | 264 dias | 792 h | R$ 55.440,00 |

---

### Por que esse serviço é necessário?

Um sistema SaaS em produção nunca está "pronto". A análise diária garante:

- ✅ **Evolução contínua** — novas funcionalidades planejadas com segurança antes de codificar
- ✅ **Zero surpresas técnicas** — problemas mapeados antes de virar bugs em produção
- ✅ **Alinhamento constante** — o sistema sempre reflete a realidade do negócio da contadora e dos clientes
- ✅ **Decisões documentadas** — cada mudança tem justificativa registrada, facilitando futuras manutenções
- ✅ **Qualidade garantida** — nenhuma entrega vai para o sistema sem ser validada no mesmo dia

---

## Resumo Consolidado por Fase

### Desenvolvimento (investimento único)

| Fase | Descrição | Período | Horas | Valor |
|---|---|---|---|---|
| Fase 1 | Estrutura base e correção de bugs | 27/04 – 29/04/2026 | 11,0 h | R$ 770,00 |
| Fase 2 | Sistema de Contas a Pagar completo | 30/04 – 06/05/2026 | 14,5 h | R$ 1.015,00 |
| Fase 3 | Notificações e alertas | 07/05 – 09/05/2026 | 8,5 h | R$ 595,00 |
| Fase 4 | Melhorias de UX e correções | 12/05 – 13/05/2026 | 3,5 h | R$ 245,00 |
| Fase 5 | E-mail automático | 14/05 – 15/05/2026 | 4,0 h | R$ 280,00 |
| Fase 6 | Contas recorrentes | 18/05 – 19/05/2026 | 6,0 h | R$ 420,00 |
| Fase 7 | Layout responsivo / mobile-first | 19/05 – 20/05/2026 | 10,5 h | R$ 735,00 |
| **Subtotal desenvolvimento** | | **27/04 – 20/05/2026** | **58,0 h** | **R$ 4.060,00** |

### Serviço recorrente (análise de requisitos diária)

| Serviço | Frequência | Horas/dia | Valor/dia | Valor/mês (22 dias) |
|---|---|---|---|---|
| Análise de requisitos | Diária | 3,0 h | R$ 210,00 | R$ 4.620,00 |

---

### Visão geral do investimento total

| Item | Valor |
|---|---|
| Desenvolvimento do sistema (já realizado) | R$ 4.060,00 |
| Análise de requisitos — mês 1 | R$ 4.620,00 |
| **Total no primeiro mês** | **R$ 8.680,00** |
| **Custo recorrente a partir do mês 2** | **R$ 4.620,00/mês** |

---

## Legenda de Dificuldade

| Nível | Critério | Horas típicas |
|---|---|---|
| ⭐ Fácil | Alterações simples, 1 arquivo, lógica direta | < 1 h |
| ⭐⭐ Médio | Planejamento necessário, 2–3 arquivos, lógica clara | 1–2,5 h |
| ⭐⭐⭐ Difícil | Múltiplos arquivos, integração backend+frontend, testes necessários | 2,5–4 h |
| ⭐⭐⭐⭐ Muito Difícil | Mudanças arquiteturais, impacto em todo o sistema, alta chance de regressão | > 4 h |

---

## Tecnologias Utilizadas

| Camada | Tecnologia |
|---|---|
| Backend | Python 3, FastAPI, SQLAlchemy, Pydantic v1 |
| Banco de dados | SQLite (dev) / MySQL / Supabase (prod) |
| Autenticação | JWT (python-jose), bcrypt (passlib) |
| Upload de arquivos | FastAPI UploadFile, UUID, StaticFiles |
| E-mail | smtplib, SMTP SSL Gmail, MIMEMultipart HTML |
| Rate limiting | slowapi |
| Frontend | HTML5, CSS3 (Vanilla), JavaScript ES6+ |
| Gráficos | Plotly.js 2.27 |
| Responsividade | CSS Media Queries, CSS Variables, Flexbox, Grid |
| PWA | Web App Manifest meta tags |

---

## Observações Finais

1. **Todo o código é original** — não foram utilizados templates ou boilerplates prontos.
2. **Zero dependências de frameworks frontend** (React, Vue, etc.) — o sistema roda em HTML puro, tornando-o extremamente leve para WebView em aplicativo mobile.
3. **Pronto para Supabase** — a troca de `sqlite:///` para a URL do Supabase na variável `DATABASE_URL` é o único ajuste necessário para produção.
4. **Escalável** — a arquitetura multi-tenant (1 contadora → N empresas) suporta crescimento sem refatoração.
5. **Segurança** — todas as rotas validam ownership; uploads verificam extensão e tamanho; tokens JWT com expiração de 24h; rate limiting ativo.

---

*Documento gerado automaticamente com base no histórico de desenvolvimento do sistema ElaConta.*  
*Valores calculados a R$ 70,00/hora conforme acordado.*
