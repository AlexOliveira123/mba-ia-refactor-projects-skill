# Project Analysis — `ecommerce-api-legacy`

## 1. Project Overview

**Domínio:** plataforma de cursos online (LMS — Learning Management System) com fluxo de checkout/pagamento. Evidenciado pelo `README.md:3` ("LMS API (com fluxo de checkout)"), pelas tabelas `courses`, `enrollments`, `payments` (`AppManager.js:13-15`), e pela mensagem de log de boot "Frankenstein LMS rodando na porta..." (`app.js:13`).

**Objetivo do sistema:** permitir que um usuário se matricule em um curso pago através de um fluxo único de checkout (que pode criar o usuário na hora, se ele não existir), processar o "pagamento", registrar a matrícula, e disponibilizar um relatório financeiro administrativo agregando receita por curso; também expõe um endpoint de exclusão de usuário.

**Principais funcionalidades** (evidenciadas pelas 3 rotas registradas em `AppManager.js:setupRoutes`):
- `POST /api/checkout` (linha 28): recebe dados de usuário, curso e cartão; cria o usuário se necessário; processa "pagamento"; cria matrícula; registra pagamento; grava log de auditoria.
- `GET /api/admin/financial-report` (linha 80): agrega, por curso, a receita total e a lista de alunos matriculados com valor pago.
- `DELETE /api/users/:id` (linha 131): remove um usuário do banco.

**Stack:** Node.js (evidenciado pela sintaxe CommonJS `require`/`module.exports` e pelo `package.json`).

**Framework:** Express `^4.18.2` (`package.json:10`; `const express = require('express')` em `app.js:1`).

**Bibliotecas relevantes:** `sqlite3` `^5.1.6` (`package.json:11`; `require('sqlite3').verbose()` em `AppManager.js:1`) — driver de acesso a SQLite baseado em callbacks (error-first). Nenhuma outra dependência declarada em `package.json` — não há biblioteca de hashing de senha (ex.: bcrypt), não há biblioteca de validação, não há biblioteca de autenticação/JWT, não há `dotenv` ou equivalente para configuração externa.

**Arquitetura:** projeto pequeno e plano — ver Seção 2.

**Principais componentes:**
- `app.js` (14 linhas): ponto de entrada — instancia o `express()`, aplica o middleware `express.json()`, instancia `AppManager`, chama `initDb()` e `setupRoutes(app)`, e inicia `app.listen`.
- `AppManager.js` (141 linhas): classe única que encapsula a conexão com o banco (`this.db`), a criação do schema e o seed de dados (`initDb`), e a definição completa das 3 rotas com toda a lógica de negócio embutida diretamente nos callbacks (`setupRoutes`).
- `utils.js` (25 linhas): exporta um objeto de configuração (`config`) contendo tanto uma porta não sensível quanto credenciais sensíveis, além de duas funções utilitárias (`logAndCache`, `badCrypto`) e duas variáveis de módulo mutáveis (`globalCache`, `totalRevenue`).

---

## 2. Architecture Summary

**Organização atual:** não há qualquer separação de camadas. Um único arquivo (`AppManager.js`) contém: inicialização de schema do banco, seed de dados, definição de rotas Express, validação de entrada, lógica de negócio de checkout (busca de curso, busca/criação de usuário, decisão de aprovação de pagamento, criação de matrícula, registro de pagamento, log de auditoria, atualização de cache), lógica de agregação do relatório financeiro (junção manual entre 3 tabelas via callbacks aninhados) e a lógica do endpoint de exclusão de usuário. Não existe Model, Controller, View ou Router isolados do restante da aplicação.

**Estrutura da aplicação:** pasta `src/` com 3 arquivos (`app.js`, `AppManager.js`, `utils.js`), sem subpastas de código. Total de 180 linhas de JavaScript entre os 3 arquivos.

**Responsabilidades de cada módulo:** conforme descrito na Seção 1. Nota adicional: `utils.js` mistura, no mesmo objeto `config` (linhas 1-7), configuração não sensível (`port`) com credenciais sensíveis (`dbUser`, `dbPass`, `paymentGatewayKey`, `smtpUser`), sem qualquer separação entre os dois tipos de dado.

**Fluxo de chamadas:** `app.js → AppManager.initDb()` / `AppManager.setupRoutes(app)` → dentro de cada rota, chamadas diretas e aninhadas a `this.db` (driver `sqlite3`) via callbacks, sem qualquer camada intermediária (nem "model", nem "repository", nem "service").

**Dependências (imports observados):** `app.js` importa `express`, `AppManager` e `{ config }` de `utils` (linhas 1-3). `AppManager.js` importa `sqlite3` e `{ config, logAndCache, badCrypto, totalRevenue }` de `utils` (linhas 1-2) — nota: `totalRevenue` é importado mas não há nenhuma referência a esse identificador em nenhum outro ponto do arquivo (ver F-004 equivalente nesta auditoria, G-004). `utils.js` não importa nada, apenas exporta.

**Acesso a dados:** feito diretamente dentro dos handlers de rota da classe `AppManager`, usando a API de callbacks do driver `sqlite3` (`this.db.get`, `this.db.all`, `this.db.run`). As queries usam parâmetros (`?`) do driver na maioria dos casos observados (ex.: `AppManager.js:37,40,50,54,57,69,92,104,106,133`), não havendo evidência de concatenação direta de valores de entrada em strings SQL neste projeto.

**Rotas:** 3 rotas registradas diretamente em `setupRoutes`: `POST /api/checkout` (linha 28), `GET /api/admin/financial-report` (linha 80), `DELETE /api/users/:id` (linha 131). Todas definidas com Express diretamente dentro da classe `AppManager`, sem uso de `express.Router()` ou separação em arquivos de rota.

**Camada de negócio:** não existe isolada; a lógica de negócio do checkout (validação de curso ativo, criação de usuário caso não exista, decisão de aprovação de pagamento com base no prefixo do número do cartão, criação de matrícula, registro de pagamento, log de auditoria, atualização de cache) está inteiramente dentro do callback da rota `POST /api/checkout` (linhas 28-78), aninhada em múltiplos níveis de callback.

**Configuração:** centralizada em `utils.js` (objeto `config`, linhas 1-7), sem uso de variáveis de ambiente — todos os valores, incluindo credenciais, estão escritos como literais no código-fonte.

**Tratamento de erros:** feito via checagem manual do parâmetro `err` em alguns (não todos) os callbacks (ex.: `if (err) return res.status(500).send("Erro DB")`, linha 41), repetida em vários pontos do arquivo. Não há middleware de tratamento de erro centralizado do Express (nenhum uso de `app.use` com assinatura de 4 argumentos, nem chamada a `next(err)`, em nenhum dos 3 arquivos analisados).

**Autenticação:** não há nenhum mecanismo de autenticação ou autorização em nenhuma rota — nenhuma verificação de identidade, token, sessão ou middleware de autenticação está presente em `app.js` ou `AppManager.js`.

**Composição da aplicação:** `app.js` atua como composition root, mas delega toda a montagem de rotas para dentro do método `setupRoutes` da própria instância de negócio (`AppManager`), misturando o papel de "ponto de entrada" com o de "controller/router" hospedado dentro da classe de domínio que também gerencia a conexão de banco.

---

## 3. Findings Summary

| Severidade | Quantidade |
|---|---|
| CRITICAL | 5 |
| HIGH | 6 |
| MEDIUM | 4 |
| LOW | 4 |
| **Total** | **19** |

Findings CRITICAL: G-001, G-002, G-005, G-006, G-007.
Findings HIGH: G-003, G-008, G-009, G-010, G-011, G-016.
Findings MEDIUM: G-012, G-013, G-014, G-015.
Findings LOW: G-004, G-017, G-018, G-019.

---

## 4. Detailed Findings

> Severidades utilizadas exclusivamente conforme definição do desafio: **CRITICAL**, **HIGH**, **MEDIUM**, **LOW**.

### G-001
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `src/utils.js`
**Linha(s):** 1-7
**Evidência:** O objeto `config` contém, escritos literalmente no código-fonte: `dbUser: "admin_master"`, `dbPass: "senha_super_secreta_prod_123"`, `paymentGatewayKey: "pk_live_1234567890abcdef"`, `smtpUser: "no-reply@fullcycle.com.br"`.
**Impacto:** Técnico: qualquer pessoa com acesso ao repositório tem acesso às credenciais de banco, à chave de gateway de pagamento (que, pelo prefixo `pk_live_`, sugere ser uma chave de ambiente de produção real) e ao usuário SMTP. Manutenção: rotação de credenciais exige alteração e reimplantação de código. Testes: nenhum impacto direto. Evolução: qualquer cópia do repositório (inclusive pública) expõe os segredos. Segurança: comprometimento potencial de banco de dados, gateway de pagamento e conta de e-mail. Performance: nenhum impacto.
**Justificativa:** Viola a separação entre configuração e código-fonte; é citado explicitamente como exemplo de severidade CRITICAL na definição do desafio ("credenciais hardcoded").

### G-002
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `src/utils.js`
**Linha(s):** 17-23
**Evidência:** A função `badCrypto(pwd)` gera um "hash" concatenando repetidamente (10.000 vezes) uma fatia de 2 caracteres da representação Base64 da senha, e retorna apenas os primeiros 10 caracteres do resultado: `hash += Buffer.from(pwd).toString('base64').substring(0, 2)`. Base64 é uma codificação reversível, não uma função de hash criptográfico; o laço de 10.000 iterações apenas repete o mesmo par de caracteres, sem adicionar entropia real.
**Impacto:** Técnico: a "senha protegida" pode ser trivialmente revertida (basta decodificar Base64), e o truncamento para 10 caracteres aumenta a chance de colisões entre senhas diferentes. Manutenção: qualquer desenvolvedor que assuma que `badCrypto` oferece proteção real está operando sob uma premissa falsa. Testes: nenhum impacto direto. Evolução: qualquer dado protegido com essa função herdará a fragilidade. Segurança: proteção de senha efetivamente inexistente — equivalente, na prática, a armazenar a senha em texto reversível. Performance: o laço de 10.000 iterações é desnecessário e desperdiça CPU sem qualquer benefício de segurança.
**Justificativa:** Uso de "criptografia" caseira e inadequada para proteger credenciais é uma falha de segurança grave, alinhada à definição CRITICAL do desafio ("expõem dados sensíveis") — o mecanismo dá uma falsa sensação de segurança sem prover proteção real.

### G-003
**Categoria:** Arquitetura / Code Smell (Global State)
**Severidade:** HIGH
**Arquivo:** `src/utils.js`
**Linha(s):** 9-10, 14
**Evidência:** `let globalCache = {}` e `let totalRevenue = 0` são variáveis de módulo mutáveis (linhas 9-10). `globalCache` é mutada dentro de `logAndCache` (linha 14: `globalCache[key] = data`), função chamada a partir do código de tratamento de requisição em `AppManager.js:59`.
**Impacto:** Técnico: estado compartilhado mutável entre requisições, sem qualquer escopo ou isolamento por requisição/usuário. Manutenção: dificulta rastrear quem alterou o estado e quando. Testes: dificulta testes isolados, pois o estado persiste entre execuções/chamadas. Evolução: dificulta escalar horizontalmente (múltiplas instâncias do processo não compartilhariam o mesmo objeto em memória, quebrando a suposição implícita de estado único). Segurança: nenhum impacto direto adicional. Performance: nenhum impacto direto relevante neste volume.
**Justificativa:** Estado global mutável é citado explicitamente como exemplo de severidade HIGH na definição do desafio ("uso de estado global mutável em toda a aplicação").

### G-004
**Categoria:** Manutenibilidade / Code Smell (Dead Code)
**Severidade:** LOW
**Arquivo:** `src/utils.js` (linhas 10, 25) e `src/AppManager.js` (linha 2)
**Linha(s):** 10, 25 (`utils.js`); 2 (`AppManager.js`)
**Evidência:** `totalRevenue` é declarado e exportado em `utils.js` (linhas 10, 25) e importado em `AppManager.js` (linha 2: `const { config, logAndCache, badCrypto, totalRevenue } = require('./utils');`), mas não há nenhuma outra referência a `totalRevenue` em `AppManager.js`.
**Impacto:** Técnico: nenhum em runtime (import não utilizado não quebra a aplicação). Manutenção: sinaliza possível funcionalidade incompleta (o nome sugere que deveria acumular receita total, mas isso nunca é implementado) ou resíduo de refatoração anterior, confundindo quem lê o código. Testes: nenhum impacto direto. Evolução: risco de um desenvolvedor assumir, pelo nome, que essa variável já contém uma métrica confiável de receita, quando na verdade nunca é populada. Segurança: nenhum. Performance: nenhum impacto relevante.
**Justificativa:** Código morto/import não utilizado reduz a legibilidade e pode induzir a erros de manutenção, consistente com os critérios de manutenibilidade citados na definição do desafio.

### G-005
**Categoria:** Arquitetura / SOLID
**Severidade:** CRITICAL
**Arquivo:** `src/AppManager.js`
**Linha(s):** 1-141 (classe completa)
**Evidência:** Uma única classe de 141 linhas concentra: gerenciamento da conexão de banco (linha 7), criação de schema e seed (linhas 10-23), definição de rotas Express (linha 25 em diante), validação de entrada (linha 35), lógica de negócio de checkout (linhas 37-78), lógica de agregação de relatório financeiro (linhas 80-129) e lógica de exclusão de usuário (linhas 131-137).
**Impacto:** Técnico: qualquer alteração em qualquer uma dessas responsabilidades exige tocar na mesma classe. Manutenção: alto risco de efeitos colaterais não intencionais entre responsabilidades não relacionadas (ex.: alterar o schema pode impactar acidentalmente a lógica de checkout, que está no mesmo arquivo). Testes: impossível testar a lógica de checkout isoladamente da conexão de banco real e do Express, pois tudo está encapsulado na mesma classe sem pontos de injeção. Evolução: dificulta escalar o time (múltiplos desenvolvedores mexendo no mesmo arquivo geram conflitos). Segurança: concentra em um único ponto todas as operações sensíveis (agrava o impacto de G-001/G-002). Performance: nenhum impacto direto por si só.
**Justificativa:** Caracteriza-se como "God Class", citado explicitamente como exemplo de severidade CRITICAL na definição do desafio, e viola diretamente o Single Responsibility Principle (SOLID) e a separação de camadas do MVC (não há Model, View ou Controller distintos — tudo reside na mesma classe).

### G-006
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `src/AppManager.js`
**Linha(s):** 131-137
**Evidência:** A rota `DELETE /api/users/:id` executa `DELETE FROM users WHERE id = ?` sem qualquer verificação de autenticação, autorização ou token — a função não contém nenhuma checagem de identidade antes de executar a exclusão. Adicionalmente, a própria resposta da rota reconhece a inconsistência de dados resultante: `res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.")` (linha 135).
**Impacto:** Técnico: qualquer requisição DELETE não autenticada remove um usuário arbitrário do sistema. Manutenção: nenhuma trava impede uso indevido. Testes: dificulta testes de integração previsíveis, pois o endpoint pode remover dados a qualquer momento. Evolução: risco cresce à medida que mais dados reais são armazenados. Segurança: exclusão não autorizada de contas de usuário por qualquer requisição externa. Performance: nenhum impacto direto.
**Justificativa:** Endpoint destrutivo sem autenticação é uma violação completa de controle de acesso, consistente com a definição CRITICAL do desafio; o dado adicional de integridade referencial "suja" é evidência complementar (ver também G-014).

### G-007
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `src/AppManager.js`
**Linha(s):** 45
**Evidência:** `console.log(\`Processando cartão ${cc} na chave ${config.paymentGatewayKey}\`)` — o número completo do cartão informado pelo cliente e a chave do gateway de pagamento são escritos juntos em texto plano no log da aplicação.
**Impacto:** Técnico: dados de cartão de pagamento (potencialmente PCI-sensíveis) e uma credencial de gateway ficam registrados em qualquer destino de log configurado para o processo (console, arquivo, agregador de logs). Manutenção: qualquer pessoa com acesso aos logs vê tanto o número do cartão quanto a chave do gateway. Testes: nenhum impacto direto. Evolução: qualquer novo destino de log (ex.: um serviço de observabilidade externo) herdaria automaticamente essa exposição. Segurança: exposição de dado de cartão de pagamento e de credencial de gateway pela mesma linha de log — dois dados sensíveis expostos simultaneamente. Performance: nenhum impacto relevante.
**Justificativa:** Exposição de dados sensíveis (dado de pagamento e segredo de integração) através de um canal observável (log) é citada como padrão de severidade CRITICAL na definição do desafio.

### G-008
**Categoria:** Arquitetura / Regra de Negócio
**Severidade:** HIGH
**Arquivo:** `src/AppManager.js`
**Linha(s):** 46
**Evidência:** `let status = cc.startsWith("4") ? "PAID" : "DENIED";` — a aprovação ou recusa do pagamento depende exclusivamente do primeiro dígito do número do cartão informado, sem qualquer chamada real a um gateway de pagamento, apesar de `config.paymentGatewayKey` ser referenciado na linha anterior (linha 45).
**Impacto:** Técnico: qualquer número de cartão iniciado em "4" é aprovado, independentemente de validade, saldo ou autenticidade. Manutenção: um desenvolvedor lendo `config.paymentGatewayKey` sendo usado pode assumir, incorretamente, que há integração real com um gateway de pagamento. Testes: não há como testar cenários reais de recusa/aprovação de gateway, pois a lógica não reflete um provedor real. Evolução: qualquer substituição futura por um gateway real exigirá reescrever completamente essa lógica, sem contrato claro definido hoje. Segurança: aprovação de pagamento sem validação real é uma falha de integridade de negócio significativa. Performance: nenhum impacto direto.
**Justificativa:** Ausência de validação real em uma operação financeira crítica é uma forte violação de integridade de regra de negócio; classificado como HIGH (e não CRITICAL) porque, diferente de uma falha de segurança de acesso a dados, o impacto está concentrado na correção funcional do domínio de pagamento, não na exposição/comprometimento direto de dados ou sistemas.

### G-009
**Categoria:** Segurança
**Severidade:** HIGH
**Arquivo:** `src/AppManager.js`
**Linha(s):** 68
**Evidência:** `let hash = badCrypto(p || "123456");` — quando o campo de senha (`p`, vindo de `req.body.pwd`) não é informado durante a criação automática de usuário no checkout, o sistema aplica silenciosamente a senha padrão `"123456"`, sem informar o usuário ou exigir troca posterior.
**Impacto:** Técnico: contas criadas sem senha explícita recebem uma credencial previsível e amplamente conhecida como fraca. Manutenção: nenhum aviso ou log indica que uma senha padrão foi aplicada, dificultando auditoria posterior. Testes: nenhum impacto direto. Evolução: qualquer novo fluxo de criação de usuário que reutilize esse padrão herdará a fragilidade. Segurança: credencial previsível combinada com o hashing inadequado de G-002 resulta em contas facilmente comprometíveis. Performance: nenhum impacto direto.
**Justificativa:** Uso de valor padrão inseguro para campo de segurança, aplicado silenciosamente, é uma prática que compromete a autenticação; combinado com G-002, eleva significativamente o risco de comprometimento de contas criadas por esse caminho.

### G-010
**Categoria:** Arquitetura / Manutenibilidade
**Severidade:** HIGH
**Arquivo:** `src/AppManager.js`
**Linha(s):** 37-77 (rota de checkout), 83-127 (rota de relatório financeiro)
**Evidência:** A rota de checkout aninha callbacks em até 5 níveis de profundidade (`db.get` → `db.get` → `processPaymentAndEnroll` → `db.run` → `db.run` → `db.run`, linhas 37-77). A rota de relatório financeiro aninha `db.all` → `forEach` → `db.all` → `forEach` → `db.get` → `db.get` (linhas 83-127), usando contadores manuais (`coursesPending`, `enrPending`) para determinar quando todas as operações assíncronas terminaram.
**Impacto:** Técnico: fluxo de controle difícil de acompanhar visualmente devido à profundidade de aninhamento. Manutenção: qualquer alteração no meio da cadeia de callbacks exige compreender todo o contexto aninhado ao redor. Testes: estrutura de callbacks aninhados dificulta isolar e testar cada etapa da lógica separadamente. Evolução: adicionar uma nova etapa ao fluxo (ex.: envio de e-mail de confirmação) provavelmente aumentaria ainda mais o aninhamento. Segurança: nenhum impacto direto adicional. Performance: nenhum impacto direto adicional.
**Justificativa:** Excesso de aninhamento de callbacks ("callback hell") dificulta fortemente a manutenção e a testabilidade, alinhando-se à definição de severidade HIGH do desafio ("dificultam muito a manutenção e testes"). Este padrão decorre diretamente do modelo de concorrência assíncrona baseado em callbacks do Node.js e das convenções do driver `sqlite3` utilizado neste projeto.

### G-011
**Categoria:** Confiabilidade
**Severidade:** HIGH
**Arquivo:** `src/AppManager.js`
**Linha(s):** 86-98, 92-122
**Evidência:** O relatório financeiro rastreia a conclusão das operações assíncronas através de contadores mutáveis decrementados dentro de callbacks (`coursesPending--` na linha 97/120, `enrPending--` na linha 117), que disparam `res.json(report)` apenas quando o contador chega a zero (linhas 98, 121). Os callbacks internos de `db.all` (linha 92) e `db.get` (linhas 104, 106) não verificam o parâmetro `err` antes de prosseguir.
**Impacto:** Técnico: se qualquer uma dessas chamadas assíncronas retornar erro (parâmetro `err` não nulo) em vez de dados válidos, o código prossegue tentando usar `enrollments`/`user`/`payment` possivelmente indefinidos, o que tanto pode lançar uma exceção não tratada quanto impedir que o contador correspondente seja decrementado — nos dois casos, a resposta ao cliente pode nunca ser enviada (requisição "pendurada") ou pode falhar de forma não controlada. Manutenção: a lógica de contagem manual é difícil de auditar e propensa a erros ao ser modificada. Testes: cenários de erro parcial (ex.: falha ao buscar apenas um pagamento entre vários) são difíceis de reproduzir e verificar. Evolução: qualquer nova consulta adicionada a este fluxo precisa lembrar de atualizar corretamente os contadores. Segurança: nenhum impacto direto. Performance: nenhum impacto direto relevante, exceto o risco de requisições penduradas consumindo recursos.
**Justificativa:** Padrão de sincronização manual de operações assíncronas sem tratamento de erro é uma fonte conhecida de condições de corrida e comportamento não determinístico, dificultando fortemente manutenção e testes — consistente com a definição HIGH do desafio.

### G-012
**Categoria:** Segurança / Manutenibilidade
**Severidade:** MEDIUM
**Arquivo:** `src/AppManager.js`
**Linha(s):** 92, 104, 106
**Evidência:** Os callbacks de `this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrollments) => {...})` (linha 92), `this.db.get("SELECT name, email FROM users WHERE id = ?", [enr.user_id], (err, user) => {...})` (linha 104) e `this.db.get("SELECT amount, status FROM payments WHERE enrollment_id = ?", [enr.id], (err, payment) => {...})` (linha 106) recebem o parâmetro `err` mas nunca o verificam antes de acessar `enrollments`, `user` ou `payment`.
**Impacto:** Técnico: um erro de banco nessas consultas é silenciosamente ignorado, prosseguindo com dados possivelmente ausentes. Manutenção: dificulta diagnosticar falhas reais de banco em produção, pois elas não são logadas nem reportadas. Testes: nenhum teste pode validar o comportamento de erro esperado, pois não há comportamento definido para esse caso. Evolução: qualquer novo consumidor deste relatório herda o mesmo risco de dados incompletos sem aviso. Segurança: nenhum impacto direto relevante. Performance: nenhum.
**Justificativa:** Tratamento incorreto de erros é citado explicitamente como exemplo de severidade MEDIUM na definição do desafio. A manifestação técnica específica — parâmetro `err` de callback error-first ignorado — decorre da convenção assíncrona do Node.js.

### G-013
**Categoria:** Performance
**Severidade:** MEDIUM
**Arquivo:** `src/AppManager.js`
**Linha(s):** 89-125
**Evidência:** Para cada curso retornado por `SELECT * FROM courses` (linha 83), o código executa uma nova consulta de matrículas (linha 92); para cada matrícula, executa uma nova consulta de usuário (linha 104) e uma nova consulta de pagamento (linha 106) — um padrão de N+1 consultas: 1 consulta de cursos + N consultas de matrículas + M consultas de usuários + M consultas de pagamentos.
**Impacto:** Técnico: o número de consultas ao banco cresce proporcionalmente ao volume de cursos, matrículas e pagamentos, em vez de ser constante. Manutenção: nenhum impacto direto. Testes: nenhum impacto direto. Evolução: piora proporcionalmente ao crescimento da base de dados. Segurança: nenhum. Performance: degradação perceptível à medida que o volume de dados cresce.
**Justificativa:** Consultas N+1 são citadas explicitamente como exemplo de severidade MEDIUM na definição do desafio.

### G-014
**Categoria:** Arquitetura / Dados
**Severidade:** MEDIUM
**Arquivo:** `src/AppManager.js`
**Linha(s):** 12-16
**Evidência:** O schema define `enrollments.user_id`, `enrollments.course_id` e `payments.enrollment_id` como colunas `INTEGER` simples (linhas 14-15), sem nenhuma cláusula `FOREIGN KEY` ou `REFERENCES` associando-as às tabelas `users`, `courses` e `enrollments`, respectivamente.
**Impacto:** Técnico: o banco não impede a criação de matrículas ou pagamentos referenciando IDs inexistentes, nem impede que a exclusão de um usuário (ver G-006) deixe registros órfãos em `enrollments` e `payments` — comportamento explicitamente reconhecido na própria mensagem de resposta do endpoint de exclusão. Manutenção: toda a responsabilidade de manter integridade referencial recai exclusivamente sobre o código da aplicação. Testes: dificulta detectar automaticamente inconsistências via constraints do próprio banco. Evolução: qualquer novo caminho de escrita que esqueça de validar referências pode corromper a integridade dos dados sem que o banco o impeça. Segurança: nenhum impacto direto. Performance: nenhum impacto direto relevante neste volume.
**Justificativa:** Ausência de integridade referencial no schema é uma limitação estrutural da camada de dados, coerente com os critérios de organização e qualidade de dados mencionados na definição do desafio.

### G-015
**Categoria:** Segurança / Validação
**Severidade:** MEDIUM
**Arquivo:** `src/AppManager.js`
**Linha(s):** 29-35
**Evidência:** A única validação de entrada da rota de checkout é a checagem de presença: `if (!u || !e || !cid || !cc) return res.status(400).send("Bad Request");` (linha 35). Não há validação de formato de e-mail, não há validação de formato/comprimento do número de cartão além do prefixo verificado posteriormente (linha 46), e o campo de senha (`p`) sequer é exigido (linha 35 não o inclui na checagem, e a ausência é tratada silenciosamente por G-009).
**Impacto:** Técnico: dados malformados (e-mail sem `@`, número de cartão com formato inválido) são aceitos e processados normalmente, desde que não vazios. Manutenção: qualquer suposição futura de que os dados chegam bem formados na camada de negócio é incorreta. Testes: nenhum teste no repositório cobre validação de formato. Evolução: qualquer novo consumidor da API herda a ausência de validação. Segurança: aumenta a superfície de dados malformados chegando às camadas de negócio e persistência. Performance: nenhum impacto direto relevante.
**Justificativa:** Validação de entrada ausente ou insuficiente em rota crítica de negócio (checkout financeiro) é citada como exemplo de severidade MEDIUM na definição do desafio ("validações ausentes nas rotas").

### G-016
**Categoria:** Arquitetura / Testabilidade
**Severidade:** HIGH
**Arquivo:** `src/AppManager.js`; `package.json`
**Linha(s):** 28-137 (`AppManager.js`); 6-8 (`package.json`)
**Evidência:** Toda a lógica de negócio (decisão de aprovação de pagamento, criação de matrícula, agregação de relatório) está definida como funções anônimas/arrow functions inline, diretamente acopladas aos objetos `req`/`res` do Express e à instância viva de `this.db` (ex.: linhas 28-78, 80-129, 131-137), sem nenhuma função de negócio exportável ou testável isoladamente. O `package.json` (linhas 6-8) define apenas o script `"start"`, sem nenhum script de teste.
**Impacto:** Técnico: não é possível invocar a lógica de aprovação de pagamento ou de cálculo de relatório sem simular uma requisição HTTP completa e uma conexão de banco real. Manutenção: qualquer verificação de comportamento exige rodar a aplicação inteira. Testes: ausência de qualquer ponto de injeção de dependência (banco, gateway) impede testes unitários; ausência de script de teste no `package.json` é evidência adicional de que testes automatizados não fazem parte do fluxo do projeto. Evolução: qualquer refatoração futura não tem uma rede de segurança de testes para validar que o comportamento foi preservado. Segurança: nenhum impacto direto adicional. Performance: nenhum impacto direto.
**Justificativa:** Acoplamento direto da lógica de negócio ao framework web e à infraestrutura de dados, sem separação (típico da ausência de uma camada de Controller/Service isolada do MVC), é uma forte violação que dificulta muito manutenção e testes — consistente com a definição HIGH do desafio.

### G-017
**Categoria:** Code Smell (Magic Value)
**Severidade:** LOW
**Arquivo:** `src/AppManager.js`
**Linha(s):** 46
**Evidência:** `cc.startsWith("4")` usa o literal `"4"` diretamente no código para decidir aprovação de pagamento, sem nomeação ou comentário explicando que representa o prefixo de cartões de bandeira Visa.
**Impacto:** Técnico: nenhum em runtime. Manutenção: um leitor sem conhecimento prévio de bandeiras de cartão não entende o significado do literal `"4"` sem investigar o contexto. Testes: dificulta escrever testes com nomes de cenário claros. Evolução: qualquer expansão para outras bandeiras exigirá localizar e modificar esse literal específico. Segurança: nenhum. Performance: nenhum.
**Justificativa:** Valor mágico não documentado é citado explicitamente como exemplo de severidade LOW na definição do desafio.

### G-018
**Categoria:** Manutenibilidade
**Severidade:** LOW
**Arquivo:** `src/AppManager.js`
**Linha(s):** 26, 29-33
**Evidência:** Variáveis de curta duração na rota de checkout recebem nomes abreviados de difícil leitura: `u`, `e`, `p`, `cid`, `cc` (linhas 29-33, para usuário, e-mail, senha, ID do curso e cartão, respectivamente), além de `self` (linha 26) como alias de `this`.
**Impacto:** Técnico: nenhum em runtime. Manutenção: reduz a legibilidade do fluxo de checkout, exigindo que o leitor infira o significado de cada abreviação pelo contexto de uso. Testes: nenhum impacto direto. Evolução: aumenta a chance de erro humano ao adicionar novos campos com nomes igualmente ambíguos. Segurança: nenhum. Performance: nenhum.
**Justificativa:** Nomenclatura de variáveis ruim é citada explicitamente como exemplo de severidade LOW na definição do desafio.

### G-019
**Categoria:** Manutenibilidade
**Severidade:** LOW
**Arquivo:** `src/AppManager.js`
**Linha(s):** 26, 43-64, 50
**Evidência:** O mesmo handler de rota mistura três estratégias diferentes de referência a contexto: um alias explícito `const self = this;` (linha 26), usado em `self.db.run` nas linhas 54 e 57; uso direto de `this.db` em arrow functions que herdam o `this` do método (ex.: linha 37, 40); e uma função regular `function(err) {...}` passada a `db.run` (linha 50) que depende do `this` próprio do driver `sqlite3` (usado deliberadamente para acessar `this.lastID` na linha 52).
**Impacto:** Técnico: nenhum erro em runtime — cada uso está correto para seu propósito específico. Manutenção: exige que o leitor raciocine cuidadosamente, a cada callback, sobre qual `this` está em escopo (o da instância `AppManager`, via `self` ou arrow function, ou o do driver `sqlite3`, via função regular), aumentando a carga cognitiva e o risco de um futuro editor introduzir um bug ao trocar inadvertidamente uma arrow function por uma função regular (ou vice-versa) sem entender a diferença. Testes: nenhum impacto direto. Evolução: qualquer novo callback adicionado a este fluxo precisa repetir corretamente essa mesma análise de contexto. Segurança: nenhum. Performance: nenhum.
**Justificativa:** Mistura de convenções para gerenciar o contexto de execução (`this`) no mesmo bloco de código é um problema de legibilidade e consistência de estilo, reduzindo a previsibilidade do código para futuros mantenedores.

---

## 5. Architectural Assessment

**Principais pontos fortes:** as consultas SQL usam parâmetros (`?`) do driver `sqlite3` de forma consistente, sem evidência de concatenação insegura de strings para formar queries; o ponto de entrada (`app.js`) é enxuto e claramente delimitado como composition root; a estrutura de arquivos é pequena o suficiente (3 arquivos, 180 linhas) para ser lida integralmente sem amostragem.

**Principais problemas:** ausência total de autenticação/autorização em qualquer rota, incluindo uma rota destrutiva (`DELETE /api/users/:id`, G-006); credenciais de banco, gateway de pagamento e SMTP hardcoded no código-fonte (G-001), agravadas por uma função de "hash" de senha que na prática não protege nada (G-002, `badCrypto`); dado de cartão de pagamento e chave de gateway expostos juntos em log de console (G-007); toda a lógica de negócio, acesso a dados e definição de rotas concentrada em uma única classe de 141 linhas (`AppManager`, G-005); decisão de aprovação de pagamento simulada por prefixo de número de cartão, sem qualquer integração real com o gateway declarado em configuração (G-008); ausência de integridade referencial no schema, deixando registros de matrícula/pagamento órfãos após exclusão de usuário (G-014); código de acesso a dados fortemente aninhado em callbacks, sem verificação do parâmetro de erro em vários pontos (G-010/G-011/G-012).

**Nível de organização:** baixo. Não há Model, View, Controller ou Router isolados; toda a aplicação reside efetivamente em uma única classe (`AppManager`), com `app.js` atuando apenas como bootstrap mínimo.

**Maturidade arquitetural:** inicial/pré-estruturação. O projeto concentra a totalidade da lógica de aplicação — acesso a dados, regra de negócio, validação e definição de rotas — em uma única classe, sem qualquer ponto de injeção de dependência que permitisse testes isolados, e sem separação entre configuração sensível e não sensível.

---

## 6. Project-Specific Characteristics

- Todo o código-fonte da aplicação (excluindo configuração de projeto) está contido em apenas 3 arquivos e 180 linhas, dentro de uma única pasta `src/`, sem subpastas.
- A camada de acesso a dados usa consistentemente parâmetros (`?`) do driver `sqlite3` em vez de concatenação de strings — diferente de um padrão de SQL Injection sistêmico, o risco predominante deste projeto está concentrado em autenticação, exposição de segredos e simulação de regra de negócio crítica, não em injeção de SQL.
- O fluxo de checkout e o relatório financeiro são implementados inteiramente através de callbacks aninhados do driver `sqlite3` (API baseada em callbacks, não em Promises/`async`/`await`), characterizando um padrão de "callback hell" com até 5 níveis de profundidade em um único handler de rota.
- A conclusão de operações assíncronas paralelas no relatório financeiro é rastreada por contadores mutáveis decrementados manualmente dentro de callbacks (`coursesPending`, `enrPending`), sem verificação do parâmetro de erro antes de decrementar ou usar os dados obtidos.
- A aprovação de pagamento é decidida inteiramente pelo primeiro dígito do número do cartão informado (`cc.startsWith("4")`), sem qualquer chamada real a um gateway de pagamento, apesar de uma chave de gateway (`config.paymentGatewayKey`) estar declarada e referenciada no mesmo trecho de código.
- Quando o campo de senha não é informado durante a criação automática de usuário no fluxo de checkout, o sistema aplica silenciosamente a senha padrão `"123456"`.
- O código mistura três estratégias distintas de referência ao contexto de execução (`this`) dentro do mesmo handler de rota: alias `self`, arrow function com `this` léxico, e função regular dependente do `this` do driver `sqlite3`.
- Uma variável (`totalRevenue`) é declarada, exportada e importada, mas nunca referenciada em nenhum outro ponto do código além da própria importação.

---

## 7. Key Learnings

- O código-fonte relevante do projeto (`app.js`, `AppManager.js`, `utils.js`, `package.json`, `api.http`, `README.md`) foi lido em sua totalidade, permitindo alto nível de confiança nos findings reportados, cada um apoiado por evidência direta de arquivo e linha.
- A verificação de uso real de `totalRevenue` (G-004) exigiu busca por referências em todo o arquivo `AppManager.js`, não apenas na lista de imports — confirmando que a variável é, de fato, um import não utilizado, e não apenas uma suposição por ausência de uso aparente.
- A confirmação de que as queries SQL usam parâmetros do driver, em vez de concatenação de strings, exigiu inspecionar individualmente cada chamada a `this.db.get`/`this.db.all`/`this.db.run` no arquivo — não foi assumida a partir do uso do driver `sqlite3` isoladamente, já que o mesmo driver permite ambos os padrões.
- A ausência de qualquer script de teste no `package.json` foi tratada como evidência complementar (não como prova isolada) da falta de testabilidade da lógica de negócio, que está diretamente acoplada aos objetos `req`/`res` do Express e à conexão viva de banco.
- Não foi possível confirmar, apenas pela leitura do código-fonte, se as rotas administrativas/destrutivas estão protegidas por alguma camada externa não representada no repositório (proxy reverso, firewall, rede privada) — a ausência de proteção observada é estritamente sobre o código da aplicação em si.
- O comportamento real de condição de corrida nos contadores manuais de conclusão assíncrona (G-011) não pôde ser observado em execução — a análise se limita ao que o código estático permite inferir sobre os cenários em que o parâmetro de erro não é verificado.

---

## 8. Considerations for the Future Skill

- Neste projeto, a ausência de SQL Injection (queries parametrizadas em praticamente todos os pontos observados) demonstra que nem todo projeto legado apresenta esse anti-pattern — a verificação de uso de parâmetros do driver precisa ser feita por si só, sem assumir que "acesso direto ao driver sem camada de repositório" implica automaticamente concatenação insegura de SQL.
- A distinção entre "estado global mutável" manifestado como conexão de banco compartilhada (em outro projeto já revisado) e manifestado como cache/contador em memória (neste projeto) mostra que a mesma categoria de anti-pattern pode ter naturezas de dado completamente diferentes — a detecção deve mirar o padrão estrutural (variável de módulo mutável, acessível de qualquer ponto), não o tipo específico de dado armazenado.
- A exposição de dados sensíveis por canal observável se manifestou aqui via log de console (cartão + chave de gateway na mesma linha); vale considerar múltiplos canais possíveis de exposição (logs, respostas de API, mensagens de erro) ao definir os sinais de detecção desse anti-pattern.
- Uma regra de negócio crítica (aprovação de pagamento) sendo simulada por uma condição trivial, apesar de existir configuração sugerindo integração real com um provedor externo, é um padrão que vale a pena tratar como achado próprio — o sinal observável é a divergência entre a infraestrutura de configuração declarada (chave de gateway) e a lógica efetivamente executada (checagem de prefixo local).
- Um fallback silencioso para valor padrão inseguro em campo de segurança (senha) é um mecanismo específico que merece verificação own-evidence, distinto da ausência total de hashing — aqui a falha está na entrada (valor padrão previsível), não apenas no armazenamento.
- Callback hell, contadores manuais de sincronização assíncrona e a complexidade de binding de `this` são todos sinais cuja aplicabilidade depende do modelo de concorrência e das convenções de linguagem/driver em uso — relevantes para conhecimento futuro, mas sua detecção não deve ser generalizada sem considerar se a stack alvo usa o mesmo modelo assíncrono baseado em callbacks.
- A confirmação de um import/variável não utilizada exige busca de referência real no arquivo consumidor, não apenas a constatação de que ela existe na lista de exports do módulo de origem.
