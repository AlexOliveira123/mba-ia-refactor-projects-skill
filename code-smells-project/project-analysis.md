# Project Analysis — `code-smells-project`

## 1. Project Overview

**Domínio:** comércio eletrônico (e-commerce). Evidenciado pelas tabelas `produtos`, `usuarios`, `pedidos`, `itens_pedido` (`database.py:15-53`) e pela mensagem de boas-vindas retornada pela rota raiz: *"Bem-vindo à API da Loja"* (`app.py:35`).

**Objetivo do sistema:** expor uma API REST para operações de uma loja online — catálogo de produtos, cadastro/autenticação de usuários, criação e acompanhamento de pedidos, e relatório gerencial de vendas.

**Principais funcionalidades** (evidenciadas pelas rotas registradas em `app.py:11-30` e pelas funções correspondentes em `controllers.py`):
- CRUD de produtos (listar, buscar por ID, buscar com filtros, criar, atualizar, deletar).
- Cadastro e listagem de usuários, e autenticação via `/login`.
- Criação de pedidos, listagem de todos os pedidos, listagem de pedidos por usuário, atualização de status de pedido.
- Relatório de vendas (`/relatorios/vendas`).
- Health check (`/health`).
- Dois endpoints administrativos definidos diretamente em `app.py`: reset do banco de dados (`/admin/reset-db`) e execução de SQL arbitrário (`/admin/query`).

**Stack:** Python (evidenciado pela sintaxe do código e pelo `requirements.txt`).

**Framework:** Flask 3.1.1 (`requirements.txt:1`; `from flask import Flask...` em `app.py:1`).

**Bibliotecas importantes:**
- `flask-cors` 5.0.1 (`requirements.txt:2`; `from flask_cors import CORS` e `CORS(app)` em `app.py:2,9`) — habilita CORS.
- `sqlite3` (biblioteca padrão do Python; `database.py:1`) — acesso ao banco de dados.

**Banco de dados:** SQLite, arquivo `loja.db` (`database.py:5,10`), com 4 tabelas: `produtos`, `usuarios`, `pedidos`, `itens_pedido` (`database.py:15-53`), criadas via `CREATE TABLE IF NOT EXISTS` e populadas com dados de exemplo no primeiro boot (`database.py:56-84`).

**Arquitetura:** projeto plano (flat), sem subpastas de código-fonte, sem separação de camadas — ver Seção 2.

**Principais componentes:**
- `app.py` (88 linhas): bootstrap da aplicação Flask, configuração, registro de rotas, e definição direta de 4 rotas adicionais (incluindo os dois endpoints administrativos).
- `controllers.py` (292 linhas): 19 funções de tratamento de requisição, uma por rota de domínio.
- `models.py` (314 linhas): 16 funções de acesso a dados e regras de negócio.
- `database.py` (86 linhas): inicialização da conexão SQLite, criação de schema e seed de dados.

---

## 2. Architecture Summary

**Organização atual:** divisão em 4 arquivos por "tipo técnico" (bootstrap/rotas, controllers, models, acesso a banco), não por domínio de negócio. Não existe camada de "View" separada — a serialização para JSON ocorre inline dentro dos controllers (chamadas a `jsonify`). Não existe módulo de configuração, nem camada de middleware dedicada.

**Responsabilidades observadas por arquivo:**
- **`app.py`**: instancia o app Flask (linha 6); define configuração inline (`SECRET_KEY`, `DEBUG` — linhas 7-8); habilita CORS (linha 9); registra 15 rotas de domínio via `add_url_rule` apontando para `controllers.py` (linhas 11-30); define diretamente, via decorator `@app.route`, mais 4 rotas: `/` (linhas 32-45), `/admin/reset-db` (linhas 47-57), `/admin/query` (linhas 59-78); e contém o bloco de bootstrap do servidor (linhas 80-88).
- **`controllers.py`**: contém 19 funções, uma por rota de domínio (produtos, usuários, pedidos, relatórios, health). Cada função realiza parsing/validação de entrada, chama uma função de `models.py`, e formata a resposta JSON, majoritariamente envolvida em um bloco `try/except Exception` genérico.
- **`models.py`**: contém 16 funções de acesso a dados, todas construindo e executando SQL diretamente via `cursor.execute()`, incluindo regras de negócio (cálculo de total de pedido, validação de estoque, cálculo de desconto no relatório de vendas).
- **`database.py`**: contém a função `get_db()`, responsável por criar a conexão SQLite uma única vez (armazenada em variável global de módulo `db_connection`, linha 4), criar as 4 tabelas caso não existam, e popular dados de exemplo na primeira execução.

**Fluxo entre arquivos:** o caminho predominante é `app.py → controllers.py → models.py → database.py`. Exceções observadas: `app.py` acessa `database.py` diretamente (linhas 4, 49, 66); `controllers.health_check()` acessa `database.py` diretamente (linha 266).

**Dependências (imports observados):** `controllers.py` importa `models` e `database` (linhas 2-3); `models.py` importa `database` (linha 1); `app.py` importa `controllers` e `database` (linhas 3-4).

**Pontos de entrada:** `app.py` é o único ponto de entrada da aplicação, através do bloco `if __name__ == "__main__":` (linhas 80-88), que também inicializa o banco chamando `get_db()` antes de subir o servidor (linha 82).

**Acesso ao banco:** centralizado na função `database.get_db()`, que retorna uma única conexão SQLite compartilhada globalmente através da variável de módulo `db_connection` (linhas 4, 8-10). Todas as queries em `models.py`, além das duas em `app.py` e uma em `controllers.py`, utilizam essa mesma conexão compartilhada.

**Roteamento:** definido inteiramente dentro de `app.py`, misturando duas convenções — `add_url_rule` (linhas 11-30) para rotas que apontam a `controllers.py`, e decorators `@app.route` (linhas 32, 47, 59) para rotas definidas localmente no próprio arquivo de bootstrap.

**Camada de negócio:** não existe como camada isolada. Regras de negócio (validação de estoque, cálculo de total do pedido, cálculo de desconto, validação de valores de status) estão distribuídas entre `controllers.py` (validações de formato/obrigatoriedade de campos de entrada) e `models.py` (regras de cálculo e consistência de dados, ex.: `criar_pedido`, `relatorio_vendas`).

**Camada de dados:** `models.py` acumula tanto o acesso a dados (construção e execução de SQL) quanto a formatação de saída (montagem manual de dicionários de resposta) para as 4 entidades do domínio, sem separação entre essas duas responsabilidades.

---

## 3. Findings Summary

| Severidade | Quantidade |
|---|---|
| CRITICAL | 10 |
| HIGH | 5 |
| MEDIUM | 8 |
| LOW | 5 |
| **Total** | **28** |

Findings CRITICAL: F-001, F-002, F-003, F-004, F-009, F-010, F-011, F-012, F-013, F-022.
Findings HIGH: F-005, F-007, F-014, F-021, F-023.
Findings MEDIUM: F-015, F-016, F-017, F-018, F-020, F-024, F-025, F-028.
Findings LOW: F-006, F-008, F-019, F-026, F-027.

---

## 4. Detailed Findings

> Severidades utilizadas exclusivamente conforme definição do desafio: **CRITICAL** (falhas graves de arquitetura/segurança, exposição de dados sensíveis, violação completa de separação de responsabilidades), **HIGH** (fortes violações de MVC/SOLID que dificultam manutenção e testes), **MEDIUM** (padronização, duplicação, performance moderada), **LOW** (legibilidade, nomenclatura, magic numbers).

### F-001
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `app.py`
**Linha(s):** 7
**Evidência:** `app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"` — a chave secreta da aplicação Flask está escrita literalmente no código-fonte.
**Impacto:** Técnico: qualquer pessoa com acesso ao repositório tem a chave usada para assinar sessões/cookies. Manutenção: rotacionar a chave exige alterar e reimplantar código. Testes: nenhum impacto direto. Evolução: qualquer cópia do repositório (inclusive pública, como exige o desafio) expõe o segredo. Segurança: comprometimento total de qualquer mecanismo que dependa dessa chave (assinatura de sessão, tokens). Performance: nenhum impacto.
**Justificativa:** Viola o princípio de separação entre configuração e código-fonte (Twelve-Factor App / boas práticas de segurança) e é listado explicitamente como exemplo de severidade CRITICAL na definição do desafio ("credenciais hardcoded").

### F-002
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `app.py`
**Linha(s):** 8, 88
**Evidência:** `app.config["DEBUG"] = True` (linha 8) e `app.run(host="0.0.0.0", port=5000, debug=True)` (linha 88) — modo debug do Flask habilitado e servidor vinculado a todas as interfaces de rede (`0.0.0.0`).
**Impacto:** Técnico: com debug ativo, exceções não tratadas expõem o debugger interativo do Werkzeug. Manutenção: nenhum. Testes: nenhum. Evolução: nenhum. Segurança: o debugger interativo do Werkzeug, quando acessível pela rede (`0.0.0.0`), é uma vulnerabilidade conhecida que pode permitir execução de código arbitrário por quem alcançar a porta exposta. Performance: modo debug tem overhead adicional (reloader, tracebacks detalhados).
**Justificativa:** Combina duas configurações que, juntas, ampliam a superfície de ataque (bind público + debugger interativo), configuração incompatível com um ambiente que se anuncia como produção (ver F-023, onde o `/health` retorna `"ambiente": "producao"`).

### F-003
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `app.py`
**Linha(s):** 47-57
**Evidência:** Rota `POST /admin/reset-db` (registrada via `@app.route`) executa `DELETE FROM itens_pedido`, `DELETE FROM pedidos`, `DELETE FROM produtos`, `DELETE FROM usuarios` e `db.commit()` sem qualquer verificação de autenticação, autorização ou token — a função não contém nenhuma checagem de identidade antes de executar as exclusões.
**Impacto:** Técnico: qualquer requisição POST não autenticada apaga todos os dados do sistema. Manutenção: nenhuma trava impede uso indevido acidental. Testes: dificulta testes de carga/integração, pois o endpoint pode zerar o estado a qualquer momento. Evolução: risco cresce à medida que mais dados reais são armazenados. Segurança: destruição completa de dados por qualquer requisição externa. Performance: nenhum impacto direto.
**Justificativa:** Viola separação de responsabilidades e controle de acesso; endpoints destrutivos sem autenticação são uma violação completa de segurança, consistente com a definição CRITICAL do desafio.

### F-004
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `app.py`
**Linha(s):** 59-78
**Evidência:** Rota `POST /admin/query` recebe um campo `"sql"` do corpo da requisição (linha 62: `query = dados.get("sql", "")`) e o executa diretamente via `cursor.execute(query)` (linha 69), sem autenticação, sem lista de permissões de comandos, sem sanitização.
**Impacto:** Técnico: permite execução de qualquer comando SQL (incluindo `DROP TABLE`, `UPDATE`, exfiltração de dados) por qualquer requisição externa. Manutenção: nenhuma proteção estrutural contra uso indevido. Testes: risco de corrupção do banco em ambientes compartilhados. Evolução: risco aumenta proporcionalmente ao volume de dados sensíveis armazenados. Segurança: comprometimento total do banco de dados — este é, isoladamente, o ponto de maior risco do sistema. Performance: consultas arbitrárias não otimizadas podem degradar performance ou travar o banco.
**Justificativa:** É a manifestação mais extrema de ausência de separação de responsabilidades e de controle de acesso — um endpoint de aplicação que expõe controle irrestrito sobre a camada de persistência, sem qualquer validação.

### F-005
**Categoria:** Arquitetura / MVC
**Severidade:** HIGH
**Arquivo:** `app.py`
**Linha(s):** 4, 49, 66
**Evidência:** `app.py` importa `get_db` diretamente de `database` (linha 4) e o utiliza nas rotas `/admin/reset-db` (linha 49) e `/admin/query` (linha 66), acessando a camada de dados sem passar pela camada de models usada por todas as outras rotas do sistema.
**Impacto:** Técnico: cria dois caminhos de acesso a dados distintos dentro da mesma aplicação. Manutenção: qualquer mudança futura na forma de acessar o banco precisa ser replicada em dois lugares (models.py e app.py). Testes: dificulta testar o ponto de entrada isoladamente da camada de dados. Evolução: aumenta o acoplamento entre o roteamento e a persistência. Segurança: nenhum impacto direto adicional (risco já coberto por F-003/F-004). Performance: nenhum impacto direto.
**Justificativa:** Viola o princípio de separação de camadas do MVC (a camada de roteamento/entrada não deveria conhecer detalhes de acesso a dados) e o Dependency Inversion Principle (SOLID), pois o módulo de mais alto nível (bootstrap) depende diretamente de um detalhe de implementação de baixo nível (conexão SQLite).

### F-006
**Categoria:** Manutenibilidade
**Severidade:** LOW
**Arquivo:** `app.py`
**Linha(s):** 11-30 (comparado a 32, 47, 59)
**Evidência:** Rotas de domínio são registradas via `app.add_url_rule(...)` (linhas 11-30), enquanto outras quatro rotas no mesmo arquivo usam o decorator `@app.route(...)` (linhas 32, 47, 59) — duas convenções distintas de registro de rota coexistem no mesmo arquivo.
**Impacto:** Técnico: nenhum em runtime (ambas as formas são válidas no Flask). Manutenção: aumenta a carga cognitiva para localizar e adicionar novas rotas, pois não há um padrão único. Testes: nenhum impacto direto. Evolução: tende a piorar conforme mais rotas são adicionadas sem convenção definida. Segurança: nenhum. Performance: nenhum.
**Justificativa:** Baixa consistência de estilo dificulta a legibilidade e a previsibilidade do código, um dos critérios de manutenibilidade citados na definição do desafio.

### F-007
**Categoria:** Arquitetura / Code Smell (Global State)
**Severidade:** HIGH
**Arquivo:** `database.py`
**Linha(s):** 4, 8-10
**Evidência:** `db_connection = None` é uma variável de módulo (linha 4); dentro de `get_db()`, a palavra-chave `global db_connection` (linha 8) é usada para atribuir e reutilizar essa única conexão SQLite (linha 10) em todas as chamadas subsequentes, de qualquer parte do sistema.
**Impacto:** Técnico: uma única conexão é compartilhada por toda a aplicação, inclusive entre requisições concorrentes. Manutenção: dificulta rastrear o ciclo de vida da conexão e isolar falhas. Testes: dificulta testes unitários isolados (não há forma de injetar uma conexão de teste sem alterar o módulo). Evolução: dificulta migrar para outro banco ou para um pool de conexões. Segurança: nenhum impacto direto. Performance: uma única conexão compartilhada sob concorrência pode se tornar gargalo (embora `check_same_thread=False` na linha 10 indique consciência do uso multi-thread, não há qualquer mecanismo de lock ou pool visível no código).
**Justificativa:** Estado global mutável é citado explicitamente na definição de severidade HIGH do desafio ("uso de estado global mutável em toda a aplicação") e viola o princípio de Inversão de Dependência (a conexão deveria ser injetada, não acessada via estado compartilhado implícito).

### F-008
**Categoria:** Manutenibilidade / Hardcoded Values
**Severidade:** LOW
**Arquivo:** `database.py`
**Linha(s):** 5
**Evidência:** `db_path = "loja.db"` — caminho do arquivo de banco de dados definido como literal no código, sem uso de variável de ambiente ou módulo de configuração.
**Impacto:** Técnico: nenhum imediato. Manutenção: alterar o caminho do banco (ex.: para ambientes diferentes) exige editar o código-fonte. Testes: dificulta apontar para um banco de teste isolado sem alterar o módulo. Evolução: dificulta configurar múltiplos ambientes (dev/staging/produção). Segurança: nenhum. Performance: nenhum.
**Justificativa:** Ausência de externalização de configuração, um dos pontos citados na definição de LOW do desafio quando não envolve dado sensível (diferente de F-001, que é uma credencial).

### F-009
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `database.py`
**Linha(s):** 76-79
**Evidência:** Dados de seed inserem usuários com senhas em texto plano: `("Admin", "admin@loja.com", "admin123", "admin")`, `("João Silva", "joao@email.com", "123456", "cliente")`, `("Maria Santos", "maria@email.com", "senha123", "cliente")` — a coluna `senha` da tabela `usuarios` (schema em `database.py:27-34`) não possui qualquer indicação de hashing, e a comparação de login (`models.py:109-111`) compara a senha recebida diretamente como string contra o valor armazenado.
**Impacto:** Técnico: senhas nunca são hasheadas em nenhum ponto do fluxo (criação em `models.py:122-131` e comparação em `models.py:109-111`). Manutenção: qualquer vazamento do banco expõe credenciais de todos os usuários em texto plano. Testes: nenhum impacto direto. Evolução: retrofit de hashing exigirá migração de dados existentes. Segurança: comprometimento total de credenciais em caso de vazamento do banco (ex.: via F-004). Performance: nenhum.
**Justificativa:** Armazenamento de senhas em texto plano é uma falha de segurança clássica e grave, alinhada à definição CRITICAL do desafio ("expõem dados sensíveis").

### F-010
**Categoria:** Arquitetura / SOLID
**Severidade:** CRITICAL
**Arquivo:** `models.py`
**Linha(s):** 1-314 (arquivo completo)
**Evidência:** Um único módulo de 314 linhas contém 16 funções de acesso a dados e regras de negócio para 4 domínios distintos e não relacionados diretamente entre si (produtos, usuários, pedidos, itens de pedido), incluindo persistência, validação de estoque, cálculo de total e cálculo de desconto.
**Impacto:** Técnico: qualquer alteração em um domínio (ex.: produtos) exige tocar em um arquivo compartilhado por todos os outros domínios. Manutenção: alto risco de efeitos colaterais não intencionais entre domínios não relacionados. Testes: impossível testar a lógica de um domínio isoladamente do módulo inteiro sem importar todo o arquivo. Evolução: dificulta escalar o time (múltiplos desenvolvedores mexendo no mesmo arquivo geram conflitos). Segurança: concentra em um único ponto todas as operações sensíveis de dados (agrava o impacto de F-011). Performance: nenhum impacto direto por si só.
**Justificativa:** Caracteriza-se como "God Class"/God Module, citado explicitamente como exemplo de severidade CRITICAL na definição do desafio ("God Class contendo... lógicas complexas... no mesmo arquivo") e viola diretamente o Single Responsibility Principle (SOLID) e a separação Model/Controller do MVC (o "Model" aqui concentra também lógica de negócio que deveria ser de uma camada de serviço/domínio distinta).

### F-011
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `models.py`
**Linha(s):** 28; 47-50; 57-61; 68; 92; 126-129; 140; 148-151; 155; 157-161; 163-166; 174; 188; 192; 220; 224; 279-281; 289-297
**Evidência:** Toda a construção de SQL em `models.py` é feita por concatenação direta de strings com valores de entrada, sem uso de parâmetros (`?`) ou escaping. Exemplos: `"SELECT * FROM produtos WHERE id = " + str(id)` (linha 28); `"INSERT INTO produtos (...) VALUES ('" + nome + "', '" + descricao + "', " + str(preco) + ...` (linhas 47-50); `query += " AND (nome LIKE '%" + termo + "%' OR descricao LIKE '%" + termo + "%')"` (linha 291, dentro de `buscar_produtos`). Nenhuma das 16 funções de `models.py` utiliza placeholders parametrizados do driver `sqlite3` (que suporta `cursor.execute(query, params)`).
**Impacto:** Técnico: qualquer valor de entrada controlado pelo usuário (nome de produto, termo de busca, e-mail, etc.) pode alterar a estrutura da query SQL executada. Manutenção: cada nova função de acesso a dados repete o mesmo padrão vulnerável. Testes: dificulta testes de seguraça automatizados, pois a superfície de ataque está espalhada por múltiplas funções. Evolução: qualquer novo endpoint que reutilize esse padrão herda a vulnerabilidade. Segurança: permite leitura, alteração ou exclusão não autorizada de dados via SQL Injection clássico. Performance: nenhum impacto direto.
**Justificativa:** SQL Injection é citado explicitamente como exemplo de severidade CRITICAL na definição do desafio, e está presente de forma sistêmica (não pontual) em praticamente toda a camada de acesso a dados do projeto.

### F-012
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `models.py`
**Linha(s):** 105-111
**Evidência:** A função `login_usuario(email, senha)` constrói a query `"SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"` (linhas 109-111) por concatenação direta dos valores recebidos, sem parametrização.
**Impacto:** Técnico: um valor malicioso no campo `senha` ou `email` pode alterar a lógica da cláusula `WHERE`, retornando um usuário sem conhecer a senha real. Manutenção: mesma causa raiz de F-011, mas isolada aqui pela gravidade específica do impacto. Testes: nenhum teste automatizado no repositório cobre esse caminho. Evolução: qualquer novo mecanismo de autenticação que reutilize esse padrão herda o risco. Segurança: pode permitir bypass completo de autenticação (ex.: acesso à conta sem senha correta, dependendo do payload). Performance: nenhum.
**Justificativa:** Tratado como finding distinto de F-011 por seu impacto diferenciado — não é "apenas" uma injeção de SQL genérica, mas uma vulnerabilidade que afeta diretamente o mecanismo de autenticação do sistema, elevando a gravidade do cenário de exploração.

### F-013
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `models.py`
**Linha(s):** 72-87, 89-103
**Evidência:** As funções `get_todos_usuarios()` (linhas 72-87) e `get_usuario_por_id(id)` (linhas 89-103) incluem o campo `"senha": row["senha"]` diretamente nos dicionários retornados, sem qualquer filtragem de campos sensíveis.
**Impacto:** Técnico: os endpoints `GET /usuarios` e `GET /usuarios/<id>` (que consomem essas funções via `controllers.py:128-144`) retornam a senha de todos os usuários (em texto plano, ver F-009) na resposta JSON. Manutenção: qualquer novo consumidor da API recebe dados sensíveis sem necessidade. Testes: nenhum impacto direto. Evolução: risco se propaga para qualquer cliente que consome esses endpoints. Segurança: exposição direta de credenciais via API pública, sem exigir nenhuma técnica de ataque adicional. Performance: nenhum.
**Justificativa:** Exposição de dados sensíveis (senhas) é citada explicitamente como critério CRITICAL na definição do desafio.

### F-014
**Categoria:** Arquitetura / SOLID (SRP)
**Severidade:** HIGH
**Arquivo:** `models.py`
**Linha(s):** 133-169
**Evidência:** A função `criar_pedido(usuario_id, itens)` realiza, em uma única função: iteração de validação de estoque item a item (linhas 139-146), cálculo de total do pedido (linha 146), inserção do pedido (linhas 148-151), e para cada item, nova consulta de preço, inserção em `itens_pedido` e atualização de estoque em `produtos` (linhas 154-166).
**Impacto:** Técnico: a função concentra validação, cálculo e persistência para duas tabelas diferentes. Manutenção: qualquer mudança em uma dessas responsabilidades (ex.: nova regra de desconto, nova validação de estoque) exige alterar a mesma função extensa. Testes: dificulta testar isoladamente a regra de cálculo de total sem também exercitar a persistência real. Evolução: dificulta reaproveitar a lógica de validação de estoque em outro contexto (ex.: um endpoint de "reserva" futuro). Segurança: nenhum impacto direto adicional. Performance: nenhum impacto direto adicional (mas ver F-011 quanto às queries usadas aqui).
**Justificativa:** Viola o Single Responsibility Principle (SOLID) — uma função concentra múltiplas razões para mudar (regra de estoque, regra de cálculo, persistência de duas entidades diferentes).

### F-015
**Categoria:** Arquitetura / Confiabilidade
**Severidade:** MEDIUM
**Arquivo:** `models.py`
**Linha(s):** 133-169
**Evidência:** A função `criar_pedido` executa múltiplos `INSERT`/`UPDATE` sequenciais (linhas 148-166) com um único `db.commit()` ao final (linha 168), sem blocos de tratamento de erro internos e sem uso explícito de controle transacional (`BEGIN`/`ROLLBACK`) visível no código.
**Impacto:** Técnico: se uma exceção ocorrer no meio do laço de itens (ex.: entre as linhas 154 e 166), não há rollback explícito no código desta função — o tratamento de exceção existente está apenas na camada de controller (`controllers.py:188-220`), fora do escopo transacional. Manutenção: dificulta garantir consistência dos dados em cenários de falha parcial. Testes: dificulta simular e verificar cenários de falha no meio da operação. Evolução: qualquer novo passo adicionado ao fluxo de criação de pedido aumenta a janela de inconsistência possível. Segurança: nenhum impacto direto. Performance: nenhum impacto direto.
**Justificativa:** Ausência de controle transacional explícito em uma operação que grava em múltiplas tabelas relacionadas é um risco de integridade de dados, relevante para a camada de persistência descrita nas guidelines de arquitetura futuras.

### F-016
**Categoria:** Code Smell (Duplicate Code)
**Severidade:** MEDIUM
**Arquivo:** `models.py`
**Linha(s):** 171-201 (função `get_pedidos_usuario`) e 203-233 (função `get_todos_pedidos`)
**Evidência:** As duas funções possuem estrutura quase idêntica: mesma construção de dicionário `pedido` (comparar linhas 178-185 com 211-218), mesmo padrão de subconsulta de itens via `cursor2` (linhas 187-189 vs 219-221) e mesmo padrão de sub-subconsulta de nome de produto via `cursor3` (linhas 191-196 vs 223-228). A única diferença relevante é a cláusula `WHERE` da consulta principal (linha 174 vs 206).
**Impacto:** Técnico: nenhum em runtime. Manutenção: qualquer correção ou mudança de formato de pedido precisa ser replicada manualmente em dois lugares — risco real de divergência futura entre as duas funções. Testes: dobra a superfície de testes necessária para cobrir o mesmo comportamento. Evolução: aumenta o custo de qualquer evolução do formato de resposta de pedidos. Segurança: nenhum impacto direto. Performance: nenhum impacto direto adicional (mas ver F-017).
**Justificativa:** Viola o princípio DRY (Don't Repeat Yourself); duplicação de código é citada explicitamente como exemplo de severidade MEDIUM na definição do desafio.

### F-017
**Categoria:** Performance
**Severidade:** MEDIUM
**Arquivo:** `models.py`
**Linha(s):** 187-199, 219-231
**Evidência:** Dentro do laço `for row in rows` (pedidos), para cada pedido é aberta uma nova consulta (`cursor2`) para buscar seus itens (linha 188/220), e dentro do laço de itens, para cada item é aberta outra nova consulta (`cursor3`) para buscar o nome do produto (linha 192/224) — um padrão de N+1 consultas: 1 consulta de pedidos + N consultas de itens + M consultas de produtos.
**Impacto:** Técnico: o número de consultas ao banco cresce linearmente com o número de pedidos e itens, em vez de ser constante. Manutenção: nenhum impacto direto. Testes: nenhum impacto direto. Evolução: piora proporcionalmente ao crescimento da base de pedidos. Segurança: nenhum. Performance: degradação perceptível de performance à medida que o volume de pedidos/itens cresce, especialmente sob carga concorrente na única conexão compartilhada (ver F-007).
**Justificativa:** Consultas N+1 são citadas explicitamente como exemplo de severidade MEDIUM na definição do desafio ("Queries N+1 no banco de dados").

### F-018
**Categoria:** Code Smell (Duplicate Code)
**Severidade:** MEDIUM
**Arquivo:** `models.py`
**Linha(s):** 9-21 (`get_todos_produtos`), 30-40 (`get_produto_por_id`), 302-313 (`buscar_produtos`)
**Evidência:** As três funções repetem, de forma quase idêntica, a montagem manual do mesmo dicionário de 8 campos (`id`, `nome`, `descricao`, `preco`, `estoque`, `categoria`, `ativo`, `criado_em`) a partir de uma `row` do SQLite.
**Impacto:** Técnico: nenhum em runtime. Manutenção: qualquer alteração no formato de serialização de produto (ex.: adicionar/remover campo) precisa ser replicada em três lugares. Testes: triplica a superfície de testes para o mesmo comportamento de serialização. Evolução: aumenta o risco de inconsistência entre os três pontos ao longo do tempo. Segurança: nenhum impacto direto. Performance: nenhum.
**Justificativa:** Mesma fundamentação de F-016 — violação do princípio DRY, com o agravante de que a lógica de serialização (que deveria pertencer a uma camada de apresentação/Model bem definida no padrão MVC) está espalhada por múltiplas funções de acesso a dados.

### F-019
**Categoria:** Code Smell (Magic Numbers)
**Severidade:** LOW
**Arquivo:** `models.py`
**Linha(s):** 256-262
**Evidência:** A função `relatorio_vendas` aplica regras de desconto usando literais numéricos sem nomeação: `if faturamento > 10000: desconto = faturamento * 0.1`, `elif faturamento > 5000: desconto = faturamento * 0.05`, `elif faturamento > 1000: desconto = faturamento * 0.02`.
**Impacto:** Técnico: nenhum em runtime. Manutenção: um leitor não consegue inferir o significado de negócio de `10000`, `5000`, `1000`, `0.1`, `0.05`, `0.02` sem contexto adicional. Testes: dificulta escrever testes com nomes de cenário claros (ex.: "faturamento acima do limiar X"). Evolução: qualquer ajuste de política comercial exige localizar e editar literais no meio da função. Segurança: nenhum. Performance: nenhum.
**Justificativa:** Magic numbers são citados explicitamente como exemplo de severidade LOW na definição do desafio.

### F-020
**Categoria:** Segurança / Validação
**Severidade:** MEDIUM
**Arquivo:** `models.py` (linhas 122-131) e `database.py` (linhas 27-34)
**Linha(s):** 122-131 (`models.py`); 27-34 (`database.py`)
**Evidência:** `criar_usuario` (`models.py:122-131`) insere um novo usuário sem verificar previamente se o e-mail já existe; o schema da tabela `usuarios` (`database.py:27-34`) não define nenhuma constraint `UNIQUE` na coluna `email`.
**Impacto:** Técnico: é possível cadastrar múltiplos usuários com o mesmo e-mail. Manutenção: qualquer lógica futura que assuma unicidade de e-mail (ex.: login, recuperação de senha) pode se comportar de forma ambígua na presença de duplicatas. Testes: nenhum teste no repositório cobre esse cenário. Evolução: dificulta implementar funcionalidades que dependam de e-mail como identificador único. Segurança: pode ser explorado para criar contas duplicadas/confundir mecanismos de identificação. Performance: nenhum impacto direto.
**Justificativa:** Validação ausente em rota de criação de recurso é citada explicitamente como exemplo de severidade MEDIUM na definição do desafio ("validações ausentes nas rotas").

### F-021
**Categoria:** Arquitetura / SOLID
**Severidade:** HIGH
**Arquivo:** `controllers.py`
**Linha(s):** 1-292 (arquivo completo)
**Evidência:** Um único módulo de 292 linhas concentra 19 funções de tratamento de requisição cobrindo 5 domínios distintos (produtos, usuários, pedidos, relatórios, health).
**Impacto:** Técnico: qualquer alteração em um domínio exige tocar em um arquivo compartilhado por todos os outros. Manutenção: alto risco de efeitos colaterais entre domínios não relacionados ao editar o mesmo arquivo. Testes: dificulta testar o tratamento de requisição de um domínio isoladamente. Evolução: dificulta divisão de trabalho entre desenvolvedores/times por domínio. Segurança: nenhum impacto direto adicional. Performance: nenhum impacto direto.
**Justificativa:** Mesma fundamentação de F-010 (SRP e "Divergent Change"), porém classificado como HIGH em vez de CRITICAL, pois, diferente de `models.py`, este arquivo não mistura adicionalmente acesso direto a banco de dados na maior parte de suas funções (exceção pontual tratada em F-024).

### F-022
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `controllers.py`
**Linha(s):** 264-292
**Evidência:** A função `health_check()` inclui no corpo da resposta JSON, entre outros campos, `"debug": True` e `"secret_key": "minha-chave-super-secreta-123"` (linhas 288-289), retornados por um endpoint `GET /health` público, sem autenticação.
**Impacto:** Técnico: a chave secreta da aplicação (mesma de F-001) é exposta publicamente via um endpoint de diagnóstico, tipicamente considerado de baixo risco. Manutenção: qualquer pessoa com acesso à API descobre o segredo sem necessidade de acesso ao código-fonte. Testes: nenhum impacto direto. Evolução: qualquer rotação futura da chave precisa considerar que ela já pode ter vazado por este caminho. Segurança: elimina completamente a confidencialidade do segredo, mesmo que F-001 fosse corrigido isoladamente (ex.: movendo para variável de ambiente), pois o valor seria de qualquer forma exposto aqui em runtime. Performance: nenhum.
**Justificativa:** Exposição de credenciais via resposta de API é uma falha de segurança CRITICAL segundo a definição do desafio, e agrava diretamente o risco já descrito em F-001.

### F-023
**Categoria:** Arquitetura / MVC
**Severidade:** HIGH
**Arquivo:** `controllers.py`
**Linha(s):** 266
**Evidência:** Dentro de `health_check()`, a linha `db = get_db()` acessa `database.py` diretamente, sem passar pela camada `models.py` usada pelas demais 18 funções de `controllers.py`.
**Impacto:** Técnico: cria mais um caminho de acesso direto ao banco fora do padrão predominante do sistema (ver também F-005, em `app.py`). Manutenção: inconsistência de padrão entre funções do mesmo arquivo. Testes: dificulta mockar a camada de dados de forma uniforme para todos os controllers. Evolução: aumenta o acoplamento entre a camada de controllers e detalhes de conexão SQLite. Segurança: nenhum impacto direto adicional. Performance: nenhum impacto direto.
**Justificativa:** Mesma fundamentação de F-005 — violação da separação de camadas do MVC e do Dependency Inversion Principle, agora identificada em um arquivo diferente (evidência distinta, mesma categoria de problema).

### F-024
**Categoria:** Segurança / Manutenibilidade
**Severidade:** MEDIUM
**Arquivo:** `controllers.py`
**Linha(s):** 10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 226-227, 234-235, 254-255, 261-262, 291-292
**Evidência:** Quinze dos dezenove funções de `controllers.py` seguem o mesmo padrão: `except Exception as e: return jsonify({"erro": str(e)}), 500`, capturando qualquer exceção genericamente e devolvendo a mensagem interna (`str(e)`) diretamente na resposta HTTP ao cliente.
**Impacto:** Técnico: nenhuma diferenciação entre tipos de erro (validação, banco, lógica) — todos retornam 500 genérico. Manutenção: bloco de código idêntico duplicado 15 vezes; qualquer mudança na política de tratamento de erro exige editar todos os pontos. Testes: dificulta testar cenários de erro específicos de forma previsível. Evolução: qualquer novo tipo de erro introduzido em `models.py` se propaga como texto livre para o cliente da API. Segurança: mensagens de exceção internas (que podem incluir fragmentos de query SQL ou detalhes de implementação) são expostas diretamente ao cliente. Performance: nenhum impacto direto.
**Justificativa:** Tratamento incorreto de erros e exposição de informações internas são citados explicitamente nos exemplos de severidade da categoria Segurança do desafio; a repetição do mesmo bloco em 15 funções também caracteriza duplicação de código.

### F-025
**Categoria:** Manutenibilidade / Validação
**Severidade:** MEDIUM
**Arquivo:** `controllers.py`
**Linha(s):** 43-54 (função `criar_produto`) comparadas a 64-96 (função `atualizar_produto`)
**Evidência:** `criar_produto` valida a categoria contra uma lista fixa (`categorias_validas`, linha 52) e rejeita categorias inválidas (linhas 53-54). `atualizar_produto` (linhas 64-96) não realiza nenhuma validação equivalente de categoria antes de chamar `models.atualizar_produto`.
**Impacto:** Técnico: é possível atualizar um produto para uma categoria inválida mesmo que a criação impeça isso. Manutenção: regras de negócio inconsistentes entre operações da mesma entidade aumentam a chance de bugs. Testes: um teste que valida a regra apenas na criação não cobre a mesma regra ausente na atualização. Evolução: qualquer nova regra de validação corre o risco de ser adicionada em apenas um dos dois pontos. Segurança: nenhum impacto direto relevante. Performance: nenhum.
**Justificativa:** Inconsistência de validação entre rotas que operam sobre a mesma entidade é um exemplo de "validações ausentes nas rotas", citado como MEDIUM na definição do desafio.

### F-026
**Categoria:** Manutenibilidade
**Severidade:** LOW
**Arquivo:** `controllers.py`
**Linha(s):** 8, 11, 57, 61, 106, 161, 179, 182, 208-210, 248, 250
**Evidência:** Uso de `print(...)` para registrar eventos da aplicação (ex.: `print("Listando " + str(len(produtos)) + " produtos")`, linha 8; `print("ENVIANDO EMAIL: ...")`, linha 208), em vez de um framework de logging configurável.
**Impacto:** Técnico: nenhum impacto funcional direto. Manutenção: impossível configurar níveis de log (debug/info/warning/error) ou direcionar logs para um destino persistente sem alterar o código. Testes: saída de `print` polui a saída de testes automatizados, se existissem. Evolução: dificulta observabilidade em produção. Segurança: nenhum impacto direto relevante. Performance: impacto mínimo, mas `print` síncrono em caminho de requisição pode adicionar latência sob alto volume.
**Justificativa:** Ausência de estratégia de logging estruturado é um problema de manutenibilidade/observabilidade, consistente com os critérios de legibilidade e manutenção citados na definição do desafio.

### F-027
**Categoria:** Manutenibilidade
**Severidade:** LOW
**Arquivo:** `controllers.py`
**Linha(s):** 9, 132, 276-290 (comparação)
**Evidência:** O formato da resposta JSON varia entre endpoints: `listar_produtos` retorna `{"dados": ..., "sucesso": True}` (linha 9); `listar_usuarios` retorna o mesmo padrão (linha 132); mas `health_check` retorna uma estrutura totalmente diferente, sem os campos `dados`/`sucesso` (`{"status": "ok", "database": ..., "counts": {...}, "versao": ..., ...}`, linhas 276-290); `buscar_usuario` (linha 142) omite o campo `sucesso` presente em outros endpoints de erro semelhantes.
**Impacto:** Técnico: nenhum erro em runtime, mas cada consumidor da API precisa conhecer o formato específico de cada endpoint. Manutenção: dificulta criar um cliente de API genérico ou um middleware de tratamento de resposta uniforme. Testes: exige testes específicos por formato de resposta, sem poder generalizar asserções. Evolução: qualquer padronização futura da API é um trabalho de migração maior por não ter sido definida desde o início. Segurança: nenhum impacto direto. Performance: nenhum.
**Justificativa:** Falta de um contrato de resposta consistente é um problema de manutenibilidade e de design de API, relacionado à ausência de uma camada de apresentação (View) padronizada no sistema.

### F-028
**Categoria:** Arquitetura / Data
**Severidade:** MEDIUM
**Arquivo:** `database.py`
**Linha(s):** 14-53
**Evidência:** O schema define `pedidos.usuario_id` (linha 39) e `itens_pedido.pedido_id`/`itens_pedido.produto_id` (linhas 48-49) como colunas `INTEGER` simples, sem nenhuma cláusula `FOREIGN KEY` ou `REFERENCES` associando-as às tabelas `usuarios` e `produtos`, respectivamente.
**Impacto:** Técnico: o banco de dados não impede a criação de um pedido referenciando um `usuario_id` ou `produto_id` inexistente. Manutenção: toda a responsabilidade de manter a integridade referencial recai exclusivamente sobre o código da aplicação (ex.: a checagem manual em `models.py:140-143`), sem rede de segurança no nível do banco. Testes: dificulta detectar automaticamente inconsistências de dados via constraints. Evolução: qualquer novo caminho de escrita que esqueça de validar a existência da referência (como os dois endpoints administrativos de `app.py`, que executam SQL livre) pode corromper a integridade dos dados sem que o banco o impeça. Segurança: nenhum impacto direto. Performance: nenhum impacto direto relevante neste volume de dados.
**Justificativa:** Ausência de integridade referencial no schema é uma limitação estrutural da camada de dados, coerente com os critérios de organização e qualidade de dados mencionados na definição do desafio.

---

## 5. Architectural Assessment

**Principais pontos fortes:** o código é consistentemente lido e organizado por "tipo técnico" em 4 arquivos (bootstrap, controllers, models, acesso a dados), o que ao menos separa fisicamente rotas de lógica de acesso a dados na maior parte do fluxo (`app.py → controllers.py → models.py → database.py`); a maioria das rotas de domínio segue o mesmo padrão de tratamento (parse → validação → chamada a `models.py` → `jsonify`); existe um endpoint de health-check funcional.

**Principais problemas:** ausência sistêmica de parametrização de SQL (SQL Injection presente em todas as 16 funções de `models.py`, F-011/F-012); dois endpoints administrativos sem qualquer autenticação, um deles permitindo execução de SQL arbitrário (F-003/F-004); segredo de aplicação hardcoded e adicionalmente exposto via `/health` (F-001/F-022); senhas armazenadas e comparadas em texto plano (F-009/F-013); concentração de responsabilidades de múltiplos domínios em dois módulos únicos, `models.py` e `controllers.py` (F-010/F-021); ausência de qualquer camada de View, configuração ou middleware dedicados.

**Nível de organização:** baixo. A separação existente é por tipo técnico, não por domínio de negócio, e não há isolamento de camada de apresentação, configuração ou tratamento de erro centralizado.

**Maturidade arquitetural:** inicial/pré-estruturação. O projeto ainda não adota nenhuma das práticas de separação de responsabilidades, controle de acesso ou gestão de configuração normalmente associadas a uma aplicação Flask madura — o padrão predominante é a concentração de responsabilidades em `models.py` e `controllers.py`, combinada com uma camada de acesso a dados construída inteiramente via concatenação de strings SQL.

---

## 6. Project-Specific Characteristics

- Projeto inteiramente plano: 4 arquivos Python na raiz, sem nenhuma subpasta de código-fonte.
- SQL Injection sistêmico: todas as 16 funções de acesso a dados de `models.py` constroem SQL por concatenação de string, sem exceção — não é um problema isolado a uma ou duas funções.
- Dois endpoints administrativos definidos diretamente em `app.py` (fora de `controllers.py`), um deles (`/admin/query`) aceitando SQL arbitrário vindo do corpo da requisição.
- O mesmo segredo de aplicação (`SECRET_KEY`) aparece hardcoded em dois pontos independentes do código (`app.py:7` e `controllers.py:289`, este último em uma resposta de API pública).
- Duplicação de lógica de serialização de produto ocorre em 3 pontos distintos do mesmo arquivo (`models.py`), e uma duplicação estrutural quase completa existe entre as funções de listagem de pedidos por usuário e de todos os pedidos.
- O contrato de resposta HTTP (`dados`/`sucesso`) não é seguido por todos os endpoints — `health_check` e `buscar_usuario` divergem do padrão usado pela maioria das rotas.
- Roteamento usa duas convenções distintas (`add_url_rule` e `@app.route`) dentro do mesmo arquivo `app.py`.

---

## 7. Key Learnings

- 100% do código-fonte Python do repositório foi lido integralmente (`app.py`, `controllers.py`, `database.py`, `models.py`, totalizando 780 linhas), permitindo alto nível de confiança em todos os findings, cada um apoiado por evidência direta de arquivo e linha.
- A ausência de suíte de testes automatizados no repositório significa que não há forma de confirmar comportamento esperado via testes antes de qualquer refatoração futura — apenas leitura estática do código sustenta os findings.
- Não foi possível confirmar, apenas pela leitura do código-fonte, se os endpoints administrativos estão protegidos por alguma camada externa não representada no repositório (proxy reverso, firewall, rede privada) — a ausência de proteção observada é estritamente sobre o código da aplicação em si.
- O `SECRET_KEY` nunca é utilizado explicitamente para nenhuma operação de sessão/token visível nos arquivos analisados, o que limitou a possibilidade de confirmar seu uso efetivo além da atribuição em `app.config`.
- O comportamento de concorrência real da conexão SQLite compartilhada sob múltiplas requisições simultâneas não pôde ser observado sem executar a aplicação — a análise se limita ao que o código estático permite inferir.
- A distinção entre decisões de design intencionais e não intencionais foi, em alguns pontos, difícil de estabelecer com certeza total, dado que o projeto não possui documentação de arquitetura (ADRs, diagramas) além de um `README.md` básico.

---

## 8. Considerations for the Future Skill

- Qualquer verificação de SQL Injection neste tipo de projeto precisa cobrir a totalidade das funções de acesso a dados, não apenas uma amostra — aqui, a ausência de parametrização é sistêmica em 16 de 16 funções.
- Distinguir, na severidade atribuída, entre "endpoint sem autenticação" e "endpoint sem autenticação que também executa comandos arbitrários" é relevante — ambos são CRITICAL, mas por razões e impactos diferentes (destruição de dados vs. controle irrestrito da persistência).
- A exposição de um mesmo segredo em mais de um ponto do código (configuração + resposta de API) é um padrão que vale a pena tratar como dois achados relacionados, não apenas um — corrigir apenas um dos pontos não resolve o problema.
- Duplicação de lógica de serialização e de listagem pode se manifestar tanto como blocos quase idênticos entre funções (mesma responsabilidade, dois lugares) quanto como um padrão estrutural repetido (mesmo N+1 replicado em duas funções análogas) — ambos relevantes para detecção.
- A inconsistência de contrato de resposta HTTP entre endpoints do mesmo projeto (`dados`/`sucesso` presente em uns, ausente em outros) é um sinal observável independentemente da tecnologia usada.
- A coexistência de duas convenções de registro de rota no mesmo framework, no mesmo arquivo, é um sinal de baixa padronização que não depende de leitura de lógica de negócio para ser detectado.
