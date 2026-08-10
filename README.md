# refactor-arch — Refatoração Arquitetural Automatizada

Este repositório contém a Skill `refactor-arch` (Claude Code) aplicada a três projetos legados com problemas reais de arquitetura, segurança e qualidade de código. A Skill analisa cada projeto, audita seu código contra um catálogo de anti-patterns e o refatora para o padrão MVC, mediante confirmação humana.

```
code-smells-project/       # Projeto 1 — Python/Flask (E-commerce), desestruturado
ecommerce-api-legacy/      # Projeto 2 — Node.js/Express (LMS + checkout), God Class
task-manager-api/          # Projeto 3 — Python/Flask (Task Manager), parcialmente organizado
reports/                   # Relatórios de auditoria (Fase 1 + Fase 2) dos 3 projetos
*/project-analysis.md      # Documento de análise padronizado (8 seções) de cada projeto
*/.claude/skills/refactor-arch/  # A Skill (idêntica nos 3 projetos)
```

---

## 1. Análise Manual

Antes de construir a Skill, os três projetos foram lidos e auditados manualmente, arquivo por arquivo, com toda evidência (arquivo + linha) confirmada no código-fonte. A análise completa de cada projeto — todos os findings, com Categoria, Severidade, Arquivo, Linha(s), Evidência, Impacto e Justificativa — está documentada em `<projeto>/project-analysis.md` e no relatório correspondente em `reports/`. Esta seção resume os totais e destaca uma amostra representativa de cada severidade.

### Projeto 1 — `code-smells-project` (Python/Flask)

| Severidade | Quantidade |
|---|---|
| CRITICAL | 10 |
| HIGH | 5 |
| MEDIUM | 8 |
| LOW | 5 |
| **Total** | **28** |

Amostra representativa:

- **[CRITICAL] SQL Injection sistêmico** (`models.py`, 16 de 16 funções) — todas as queries são construídas por concatenação de string, sem parametrização; qualquer input do usuário pode alterar a query executada. Relevante porque é o risco de maior alcance do projeto: não é uma falha pontual, é o padrão de acesso a dados inteiro.
- **[CRITICAL] Endpoint que executa SQL arbitrário sem autenticação** (`/admin/query`, `app.py:59-78`) — aceita um campo `"sql"` do corpo da requisição e executa diretamente. Relevante por ser controle total e irrestrito sobre o banco, exposto publicamente.
- **[HIGH] Estado global mutável** (`database.py:4,8-10`) — uma única conexão SQLite compartilhada via `global`, sem ciclo de vida por requisição. Relevante para testabilidade e concorrência.
- **[MEDIUM] Consultas N+1** (`models.py:187-231`) — uma consulta adicional por pedido e por item, em vez de uma única consulta com JOIN. Relevante porque a performance degrada proporcionalmente ao volume de dados.
- **[MEDIUM] Tratamento de erro genérico e repetido** (`controllers.py`, 15 ocorrências) — `except Exception as e: return jsonify({"erro": str(e)})`, expondo mensagens internas ao cliente. Relevante por vazar detalhes de implementação e não diferenciar tipos de erro.
- **[LOW] Magic numbers nos limiares de desconto** (`models.py:256-262`) — `10000`, `5000`, `1000`, `0.1`, `0.05`, `0.02` sem nomeação. Relevante para legibilidade e para tornar a regra de negócio auditável.
- **[LOW] Logging via `print()`** (`app.py`, `controllers.py`, 14 ocorrências) — sem controle de nível ou destino configurável.

### Projeto 2 — `ecommerce-api-legacy` (Node.js/Express)

| Severidade | Quantidade |
|---|---|
| CRITICAL | 5 |
| HIGH | 6 |
| MEDIUM | 4 |
| LOW | 4 |
| **Total** | **19** |

Amostra representativa:

- **[CRITICAL] "Hashing" de senha reversível** (`utils.js:17-23`, `badCrypto`) — repete uma codificação Base64 10.000 vezes e trunca o resultado; Base64 é reversível, não é um hash criptográfico. Relevante porque dá uma falsa sensação de segurança sem prover proteção real.
- **[CRITICAL] Dado de cartão de pagamento e chave de gateway em log de console** (`AppManager.js:45`) — ambos em texto plano, na mesma linha de log. Relevante por ser exposição de dado potencialmente PCI-sensível junto com uma credencial.
- **[HIGH] Aprovação de pagamento por prefixo de cartão** (`AppManager.js:46`) — `cc.startsWith("4")` decide "PAID"/"DENIED", sem integração real com gateway algum. Relevante por ser uma regra de negócio financeira crítica simulada, sem validação real.
- **[HIGH] Callback hell** (`AppManager.js:37-77`) — até 5 níveis de callbacks aninhados no fluxo de checkout, dificultando fortemente manutenção e testes.
- **[MEDIUM] Parâmetro `err` de callback ignorado** (`AppManager.js:92,104,106`) — erros de banco são silenciosamente tratados como sucesso.
- **[MEDIUM] Ausência de integridade referencial** (`AppManager.js:12-16`) — `enrollments`/`payments` sem `FOREIGN KEY`, permitindo registros órfãos (evidenciado pela própria resposta do endpoint de exclusão de usuário).
- **[LOW] Nomenclatura abreviada** (`AppManager.js:29-33`) — `u`, `e`, `p`, `cid`, `cc`, exigindo mapeamento mental para o significado de negócio.

### Projeto 3 — `task-manager-api` (Python/Flask, parcialmente organizado)

| Severidade | Quantidade |
|---|---|
| CRITICAL | 7 |
| HIGH | 2 |
| MEDIUM | 8 |
| LOW | 3 |
| **Total** | **20** |

Amostra representativa:

- **[CRITICAL] Autenticação decorativa** (`user_routes.py:210` + ausência total de verificação) — o login emite `'fake-jwt-token-' + str(user.id)`, sem assinatura nem expiração, e nenhuma rota do projeto valida esse ou qualquer outro token. Relevante por ser mais enganoso que a ausência total de login: parece existir um controle de acesso que não existe de fato.
- **[CRITICAL] Hash de senha com MD5 sem salt** (`models/user.py:27-32`) — algoritmo criptograficamente quebrado para esse uso, com hashes idênticos para senhas idênticas entre usuários (visível nos próprios dados de seed).
- **[HIGH] Camada de serviço e maior parte de `utils/` nunca utilizadas** (`services/notification_service.py`; 7 de 9 funções e todas as 7 constantes de `utils/helpers.py`) — confirmado por busca de referência em todo o repositório, não por inferência da estrutura de pastas. Relevante porque mostra que a separação física de camadas não garante separação efetiva de responsabilidades.
- **[HIGH] Reimplementação manual ignorando `Task.is_overdue()`** (`models/task.py:50-60` vs. 5 reimplementações em 3 arquivos) — a abstração correta existe e é ignorada.
- **[MEDIUM] CORS irrestrito** (`app.py:15`) — `CORS(app)` sem restrição de origem, ampliando a superfície de exploração da ausência total de autenticação.
- **[MEDIUM] Duas dependências instaladas e nunca importadas** (`marshmallow`, `python-dotenv`) — evidência concreta de intenção arquitetural não realizada.
- **[LOW] Efeito colateral de `db.create_all()` no nível de módulo** (`app.py:30-31`) — dispara a criação do schema sempre que o módulo é importado, inclusive por `seed.py`.

---

## 2. Construção da Skill

### Decisões de design

O `SKILL.md` implementa as 3 fases exigidas — Análise, Auditoria (com gate de confirmação humana) e Refatoração — como um roteiro de execução puro: ele não contém nenhum fato específico de projeto (nenhuma linguagem, framework, nome de arquivo ou finding hardcoded). Todo o conhecimento específico de cada codebase vive em 5 arquivos de referência dentro de `reference/`:

| Arquivo | Conteúdo |
|---|---|
| `project-analysis.md` | Heurísticas de detecção de linguagem/framework/banco/arquitetura para a Fase 1, incluindo como verificar alcançabilidade de código em vez de confiar em nomes de pasta |
| `anti-pattern-catalog.md` | Catálogo de anti-patterns com sinal de detecção, severidade fixa e evidência de referência para a Fase 2 |
| `report-template.md` | Formato de saída obrigatório das 3 fases |
| `mvc-guidelines.md` | Estrutura de destino e regras de camada (Models/Views-Routes/Controllers) para a Fase 3 |
| `refactoring-playbook.md` | Padrões concretos de transformação (antes/depois) para a Fase 3 |

Essa separação — motor genérico em `SKILL.md`, conhecimento específico em `reference/` — é o que permite que **o mesmo `SKILL.md`, byte a byte idêntico, esteja copiado nos 3 projetos**, cada um com seu próprio `reference/` construído a partir de sua própria auditoria.

### Catálogo de anti-patterns: o que foi incluído e por quê

Cada projeto tem seu próprio catálogo com exatamente 20 entradas (`AP-01` a `AP-20`), cobrindo os 4 níveis de severidade e incluindo obrigatoriamente uma entrada de verificação de APIs deprecated (`AP-20`), conforme exigido. As entradas não foram copiadas entre projetos: cada uma foi escrita a partir da evidência real daquele projeto (arquivo + linha), e cobre 100% dos findings da respectiva auditoria manual — 28 findings em 19 entradas no Projeto 1 (algumas entradas consolidam mais de um finding do mesmo anti-pattern), 19 findings em 19 entradas no Projeto 2 (mapeamento 1:1), e 20 findings em 17 entradas + 3 verificações estruturais no Projeto 3.

O catálogo do Projeto 3 (`task-manager-api`) recebeu atenção adicional porque o projeto já possui alguma separação em camadas (`models/`, `routes/`, `services/`, `utils/`): cada entrada cujo sinal depende de código estar "vivo" ou "morto" (camada de serviço não utilizada, utilitários ignorados, lógica duplicada apesar de uma abstração já existir) exige explicitamente uma busca real de referência em todo o repositório antes de reportar o finding — nunca inferir a partir do nome ou existência de uma pasta.

### Como a agnosticismo de tecnologia foi garantido

1. **O motor (`SKILL.md`) não conhece tecnologia alguma.** Ele instrui *o que fazer* (ler os arquivos de referência, verificar cada entrada do catálogo, produzir o relatório no formato exigido, pausar para confirmação, aplicar as transformações) sem jamais mencionar Python, Flask, Node.js ou qualquer nome de arquivo.
2. **Todo fato específico vive em `reference/`.** A mesma Skill funcionou sobre Python/Flask desestruturado (Projeto 1), Node.js/Express com uma God Class (Projeto 2) e Python/Flask parcialmente organizado (Projeto 3) porque, para o motor, a diferença entre esses três cenários é só qual `reference/` ele está lendo.
3. **Regra explícita contra o viés de "pasta = boa arquitetura".** A regra global 3 do `SKILL.md` proíbe concluir que um projeto está bem ou mal arquitetado só pela presença/ausência de pastas como `models/`/`services/`/`controllers/` — toda alegação sobre uma camada precisa de uma busca de alcançabilidade real. Essa regra nasceu diretamente da auditoria do Projeto 3, que não tem God Class e, ainda assim, tem uma ausência total de autenticação classificada como CRITICAL.

### Desafios encontrados e como foram resolvidos

- **Risco de falso negativo em projetos parcialmente organizados.** A auditoria do Projeto 3 mostrou que "ausência de um arquivo gigante" não implica boa separação de responsabilidades — o projeto tem uma camada de serviço inteira e a maior parte de uma camada de utilitários nunca executadas, e uma abstração de Model correta sendo ignorada e reimplementada 5 vezes. A resposta foi tratar isso como uma categoria própria de risco (camada estrutural mas não efetivamente usada), verificável apenas por busca de referência, não por inspeção de pasta.
- **Risco de falso positivo ao avaliar mecanismos de proteção.** Presença de "alguma função de hash" ou de "uma rota de login" não é, por si só, evidência de segurança — o Projeto 2 usa uma codificação Base64 disfarçada de hash, e o Projeto 3 usa MD5 sem salt (um hash real, porém inadequado) e emite um token de login que nenhuma rota valida. O catálogo de cada projeto exige avaliar a qualidade do mecanismo (algoritmo, salt, validação efetiva), não apenas sua presença.
- **Padrões dependentes de tecnologia vs. universais.** Alguns problemas (callback hell, condição de corrida em contadores manuais, binding de `this`) só existem no modelo assíncrono baseado em callbacks do Node.js e não têm equivalente em Python síncrono; outros (credenciais hardcoded, N+1, valores mágicos) se confirmaram nos 3 projetos com manifestações sintáticas diferentes. Cada catálogo documenta isso explicitamente para não generalizar um padrão específico de stack como se fosse universal.
- **Unificação final do `SKILL.md`.** As três versões originais continham frases específicas de projeto (nomes de arquivo, listas de endpoints, contagens de padrões `PB-XX`, e afirmações como "this Skill was built specifically for this project... it is not a generic skill"). A unificação removeu todo esse conteúdo, generalizando cada passo (ex.: "chame cada endpoint mapeado na Fase 1" em vez de listar endpoints; "crie/ajuste a estrutura definida em `mvc-guidelines.md`" em vez de listar pastas fixas), preservando as mesmas 3 fases, o mesmo gate de confirmação e as mesmas regras globais de evidência.

---

## 3. Resultados

### Resumo dos relatórios de auditoria (Fase 2)

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total de findings (Fase 2) |
|---|---|---|---|---|---|
| 1 — code-smells-project | 7 | 3 | 6 | 3 | 19 |
| 2 — ecommerce-api-legacy | 5 | 6 | 4 | 4 | 19 |
| 3 — task-manager-api | 5 | 2 | 7 | 3 | 17 |

Os relatórios completos (`reports/audit-project-{1,2,3}.md`) trazem cada finding no formato `[SEVERIDADE] Nome do anti-pattern (ID do catálogo)`, com arquivo, linha(s), descrição factual, impacto e recomendação — refletindo o estado do código antes da Fase 3, reconfirmado contra o commit inicial do repositório (`6d1ce62`).

### Comparação antes/depois da estrutura

**Projeto 1 — `code-smells-project`:**

```
Antes                          Depois
app.py (88 linhas)             app.py (shim de compatibilidade → src/app.py)
controllers.py (292 linhas)    src/
models.py (314 linhas)           config/settings.py
database.py (86 linhas)          database.py
                                  models/ (admin, order, product, user)
                                  views/ (admin, order, product, user routes)
                                  controllers/ (admin, order, product, user)
                                  middlewares/ (admin_auth, error_handler)
```

**Projeto 2 — `ecommerce-api-legacy`:**

```
Antes                          Depois
src/app.js (14 linhas)         src/
src/AppManager.js (141 linhas)   app.js, cache.js, database.js
src/utils.js (25 linhas)         config/settings.js
                                  models/ (audit log, course, enrollment, payment, report, user)
                                  controllers/ (checkout, report, user)
                                  routes/ (checkout, report, user)
                                  services/paymentGateway.js
                                  middlewares/ (adminAuth, errorHandler)
```

**Projeto 3 — `task-manager-api`:**

```
Antes                          Depois
app.py, database.py, seed.py   app.py, database.py, seed.py, config.py (novo)
models/ (user, task, category) models/ (mantido)
routes/ (user, task, report)   routes/ (mantido)
services/notification_service  controllers/ (novo: report, task, user)
utils/helpers.py                middlewares/ (novo: auth.py, error_handler.py)
                                 services/ e utils/ removidos (código morto confirmado por busca de referência)
```

O Projeto 3 é o único em que a Fase 3 não recria a estrutura do zero — ele evolui a organização já existente (mantém `models/`, `routes/`, `utils/`), adicionando `controllers/`, `middlewares/` e `config.py`, e removendo especificamente o que a auditoria confirmou como não utilizado (`services/notification_service.py` e a maior parte de `utils/helpers.py`), em vez de assumir que a estrutura pré-existente já estava correta.

### Checklist de validação

```markdown
### Fase 1 — Análise
- [x] Linguagem detectada corretamente nos 3 projetos (Python nos projetos 1 e 3, JavaScript/Node.js no projeto 2)
- [x] Framework detectado corretamente (Flask 3.1.1, Express ^4.18.2, Flask 3.0.0 + flask-sqlalchemy 3.1.1)
- [x] Domínio da aplicação descrito corretamente (e-commerce, LMS com checkout, task manager)
- [x] Número de arquivos analisados condiz com a realidade (4, 3 e 11 arquivos, respectivamente)

### Fase 2 — Auditoria
- [x] Relatório segue o template definido nos arquivos de referência
- [x] Cada finding tem arquivo e linhas exatos
- [x] Findings ordenados por severidade (CRITICAL → LOW)
- [x] Mínimo de 5 findings identificados (19, 19 e 17 findings de catálogo, respectivamente — cobrindo 28, 19 e 20 findings da auditoria manual)
- [x] Detecção de APIs deprecated incluída nos 3 projetos (nenhuma ocorrência real encontrada em nenhum dos 3, verificação registrada explicitamente)
- [x] Skill pausa e pede confirmação antes da Fase 3

### Fase 3 — Refatoração
- [x] Estrutura de diretórios segue padrão MVC nos 3 projetos
- [x] Configuração extraída para módulo de config (`src/config/settings.py`, `src/config/settings.js`, `config.py`)
- [x] Models criados/mantidos para abstrair dados
- [x] Views/Routes separadas do roteamento
- [x] Controllers concentram o fluxo da aplicação
- [x] Error handling centralizado (`middlewares/error_handler.*`)
- [x] Entry point claro (`app.py`/`src/app.js`, documentado no README de cada projeto)
- [x] Aplicação inicia sem erros e endpoints originais respondem — validado durante a execução da Fase 3 registrada no histórico do repositório; os passos de verificação estão documentados no README de cada projeto
```

### Observações sobre o comportamento em stacks diferentes

- Nos dois projetos completamente desestruturados (1 e 2), a Fase 3 recriou a estrutura de diretórios do zero. No projeto parcialmente organizado (3), ela evoluiu a estrutura existente em vez de descartá-la — a mesma Skill se adaptou ao nível de maturidade estrutural de cada projeto sem receber essa distinção como uma instrução hardcoded.
- O único anti-pattern verdadeiramente específico de tecnologia identificado foi o conjunto ligado ao modelo assíncrono de callbacks do Node.js (callback hell, condição de corrida em contadores manuais, binding de `this`) — presente apenas no Projeto 2 e sem equivalente possível nos projetos Flask, que executam de forma síncrona.
- O Projeto 3 confirmou que "não ter uma God Class" não é suficiente para concluir boa arquitetura: ele tem separação física de camadas e, ainda assim, concentra 5 CRITICAL findings — incluindo uma autenticação puramente decorativa, um risco de gravidade equivalente ou maior à ausência total de login dos outros dois projetos.

---

## 4. Como Executar

### Pré-requisitos

- [Claude Code](https://docs.claude.com/en/docs/claude-code/overview) instalado e configurado.
- Para cada projeto: o runtime da sua stack (Python 3.11+ para os projetos 1 e 3; Node.js para o projeto 2).

### Executar a Skill em cada projeto

A Skill já está copiada, idêntica, em `.claude/skills/refactor-arch/` dentro dos 3 projetos.

```bash
# Projeto 1 — code-smells-project
cd code-smells-project
claude "/refactor-arch"

# Projeto 2 — ecommerce-api-legacy
cd ../ecommerce-api-legacy
claude "/refactor-arch"

# Projeto 3 — task-manager-api
cd ../task-manager-api
claude "/refactor-arch"
```

Em cada execução: a Fase 1 imprime a análise do projeto; a Fase 2 imprime o relatório de auditoria e pausa perguntando `Phase 2 complete. Proceed with refactoring (Phase 3)? [y/n]`; respondendo `y`, a Fase 3 aplica as transformações e imprime o resumo final. Os relatórios já gerados por essas execuções estão salvos em `reports/audit-project-{1,2,3}.md`.

### Rodar cada projeto já refatorado

Cada projeto documenta seus próprios pré-requisitos, variáveis de ambiente e exemplos de chamada no seu `README.md`. Resumo:

```bash
# Projeto 1 — code-smells-project (sobe em http://localhost:5000)
cd code-smells-project
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python app.py

# Projeto 2 — ecommerce-api-legacy (sobe em http://localhost:3000)
cd ecommerce-api-legacy
npm install && npm start

# Projeto 3 — task-manager-api (sobe em http://localhost:5000)
cd task-manager-api
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python seed.py   # popular o banco antes do primeiro boot
.venv/bin/python app.py
```

### Como validar que a refatoração funcionou

1. Confirme que o processo sobe sem erros (mensagem de boot no terminal, sem traceback).
2. Chame as rotas originais mapeadas na Fase 1 de cada projeto (ex.: `curl http://localhost:5000/health`) e confirme que todas respondem.
3. Confirme os novos comportamentos de segurança introduzidos pela Fase 3 — por exemplo, no Projeto 3: `POST /login` retorna um token assinado real, e rotas destrutivas/de alteração de `role` agora exigem `Authorization: Bearer <token>` (401 sem token, 403 para não-admin tentando alterar `role`); no Projeto 1: `/admin/reset-db` e `/admin/query` agora exigem o header `X-Admin-Token`.
4. Compare o relatório de auditoria em `reports/` com o código atual: os findings CRITICAL/HIGH ali listados não devem mais estar presentes no código refatorado.
