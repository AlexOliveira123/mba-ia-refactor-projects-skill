# Project Analysis — `task-manager-api`

## 1. Project Overview

**Domínio:** gerenciamento de tarefas (task manager) com usuários, categorias e tarefas. Evidenciado pelas tabelas `users`, `tasks`, `categories` (`models/user.py:6`, `models/task.py:6`, `models/category.py:5`) e pela resposta da rota raiz `{'message': 'Task Manager API', 'version': '1.0'}` (`app.py:26-28`).

**Objetivo do sistema:** permitir cadastro e autenticação de usuários, criação/organização de tarefas por categoria e responsável, acompanhamento de status/prioridade/prazo, e geração de relatórios agregados (resumo geral, relatório por usuário, estatísticas de tarefas).

**Stack:** Python (sintaxe do código, `requirements.txt`).

**Framework:** Flask 3.0.0 (`requirements.txt:1`), com `flask-sqlalchemy` 3.1.1 como camada de ORM (`requirements.txt:2`; `database.py:1`).

**Arquitetura:** projeto distribui o código em pacotes por responsabilidade técnica — ver Seção 2.

**Principais componentes:**
- `app.py`: cria a aplicação Flask, configura banco (URI SQLite), `SECRET_KEY` e CORS, registra os 3 blueprints (`task_bp`, `user_bp`, `report_bp`), define as rotas `/health` e `/`, e cria as tabelas via `db.create_all()`.
- `database.py`: exporta a instância única `db = SQLAlchemy()`, usada por todos os models.
- `models/` (`user.py`, `task.py`, `category.py`): cada entidade (`User`, `Task`, `Category`) é uma classe SQLAlchemy com colunas, relacionamentos (`db.relationship`) e alguns métodos próprios (`to_dict`, `set_password`/`check_password` em `User`; `validate_status`/`validate_priority`/`is_overdue` em `Task`).
- `routes/` (`user_routes.py`, `task_routes.py`, `report_routes.py`): cada blueprint concentra as funções de tratamento de requisição HTTP para seu domínio (usuários, tarefas, relatórios/categorias), incluindo parsing, validação de entrada, chamadas ao ORM (`Model.query...`, `db.session...`) e formatação de resposta JSON.
- `services/notification_service.py`: contém `NotificationService`, uma classe com métodos para enviar e-mail e registrar notificações.
- `utils/helpers.py`: contém funções utilitárias (`format_date`, `calculate_percentage`, `validate_email`, `sanitize_string`, `generate_id`, `log_action`, `parse_date`, `is_valid_color`, `process_task_data`) e constantes (`VALID_STATUSES`, `VALID_ROLES`, `MAX_TITLE_LENGTH`, `MIN_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`, `DEFAULT_PRIORITY`, `DEFAULT_COLOR`).
- `seed.py`: script de povoamento de dados de exemplo, que importa `app` e `db` de `app.py`.

**Estrutura de diretórios (evidenciada por `find`):**
```
task-manager-api/
├── app.py
├── database.py
├── seed.py
├── requirements.txt
├── models/ (__init__.py, user.py, task.py, category.py)
├── routes/ (__init__.py, user_routes.py, task_routes.py, report_routes.py)
├── services/ (__init__.py, notification_service.py)
└── utils/ (__init__.py, helpers.py)
```

---

## 2. Architecture Summary

**Organização atual:** o projeto apresenta uma divisão física de responsabilidades por camada (`models/`, `routes/`, `services/`, `utils/`), claramente diferente de um projeto totalmente plano. Ao mesmo tempo, a leitura detalhada do código (Seção 4) mostra que essa separação física nem sempre corresponde a uma separação efetiva de responsabilidades em tempo de execução.

**Entry point:** `app.py`, através do bloco `if __name__ == '__main__':` (linhas 33-34), que chama `app.run(debug=True, host='0.0.0.0', port=5000)`. Nota: a criação de tabelas (`db.create_all()`, linhas 30-31) ocorre fora desse bloco, no nível superior do módulo, sendo executada sempre que `app.py` é importado (não apenas quando executado diretamente) — evidenciado por `seed.py:2` (`from app import app, db`).

**Rotas:** registradas via 3 blueprints Flask:
- `task_bp` (`routes/task_routes.py`): `GET/POST /tasks`, `GET/PUT/DELETE /tasks/<id>`, `GET /tasks/search`, `GET /tasks/stats`.
- `user_bp` (`routes/user_routes.py`): `GET/POST /users`, `GET/PUT/DELETE /users/<id>`, `GET /users/<id>/tasks`, `POST /login`.
- `report_bp` (`routes/report_routes.py`): `GET /reports/summary`, `GET /reports/user/<id>`, `GET/POST /categories`, `PUT/DELETE /categories/<id>`.
Mais duas rotas registradas diretamente em `app.py`: `GET /health`, `GET /`.

**Controllers:** não existe uma camada nomeada "controllers" — as funções de rota dentro de cada blueprint acumulam esse papel (parsing de entrada, orquestração, chamada ao ORM, formatação de saída).

**Services:** existe uma única classe, `NotificationService` (`services/notification_service.py`), com métodos `send_email`, `notify_task_assigned`, `notify_task_overdue`, `get_notifications`. Evidência de não utilização: busca textual por `NotificationService` em todo o repositório retorna apenas ocorrências dentro do próprio arquivo `services/notification_service.py` — nenhuma rota, nenhum model e nenhum outro módulo importa ou instancia essa classe.

**Models:** `User`, `Task`, `Category` (SQLAlchemy). `Task` declara `db.ForeignKey('users.id')` e `db.ForeignKey('categories.id')` (`models/task.py:13-14`), com `db.relationship` correspondente (linhas 20-21).

**Acesso a dados:** feito através do ORM SQLAlchemy (`Model.query.get/all/filter_by/count`, `db.session.add/commit/rollback/delete`) em todas as rotas observadas — nenhuma ocorrência de SQL cru concatenado foi encontrada em nenhum arquivo do projeto.

**Configuração:** centralizada em `app.py` (linhas 11-13): URI do banco, flag de tracking do SQLAlchemy e `SECRET_KEY`, todos como literais no código. Evidência de não utilização de ferramenta de configuração externa: `python-dotenv` está listado em `requirements.txt:6`, mas não há nenhuma ocorrência de `import dotenv` ou `load_dotenv` em nenhum arquivo do projeto.

**Tratamento de erros:** predominantemente via blocos `try/except` ao redor de operações de escrita no banco (`db.session.commit()`), com `except Exception as e:` em alguns pontos (`routes/user_routes.py:87`, `routes/task_routes.py:151,221`) e `except:` (sem tipo) em outros (`routes/task_routes.py:62`, `routes/report_routes.py:186,207,221`). Não há middleware de tratamento de erro centralizado do Flask (nenhum uso de `@app.errorhandler` em nenhum arquivo).

**Dependências (imports observados):** `app.py` importa `Flask`, `CORS`, `db`, e os 3 blueprints. Cada arquivo de `routes/` importa `db` e os models que utiliza. `report_routes.py` importa adicionalmente `format_date, calculate_percentage` de `utils.helpers` (linha 7). `models/user.py` e `models/task.py` importam `db` de `database`. `services/notification_service.py` não é importado por nenhum outro arquivo do projeto (confirmado por busca textual).

**Fluxo entre módulos:** `app.py → routes/*.py (blueprints) → models/*.py (ORM) → database.py (instância SQLAlchemy)`. Não há evidência de qualquer rota chamando `services/notification_service.py` ou a maior parte de `utils/helpers.py` — ambos os módulos existem na estrutura de diretórios, mas estão desconectados do fluxo de execução real observável a partir dos pontos de entrada (rotas e `app.py`).

---

## 3. Findings Summary

| Severidade | Quantidade |
|---|---|
| CRITICAL | 7 |
| HIGH | 2 |
| MEDIUM | 8 |
| LOW | 3 |
| **Total** | **20** |

Findings CRITICAL: H-001, H-002, H-003, H-004, H-005, H-006, H-008.
Findings HIGH: H-009, H-012.
Findings MEDIUM: H-007, H-010, H-013, H-014, H-015, H-016, H-017, H-020.
Findings LOW: H-011, H-018, H-019.

---

## 4. Detailed Findings

> Severidades utilizadas exclusivamente conforme definição do desafio: **CRITICAL**, **HIGH**, **MEDIUM**, **LOW**.

### H-001
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `app.py`
**Linha(s):** 13
**Evidência:** `app.config['SECRET_KEY'] = 'super-secret-key-123'` — chave secreta escrita literalmente no código-fonte, apesar de `python-dotenv` (biblioteca para carregar configuração de variáveis de ambiente) estar declarada em `requirements.txt:6`.
**Impacto:** Técnico: qualquer pessoa com acesso ao repositório tem a chave usada pela aplicação Flask. Manutenção: rotação exige alteração e reimplantação de código. Testes: nenhum impacto direto. Evolução: qualquer cópia do repositório expõe o segredo. Segurança: comprometimento de qualquer mecanismo que dependa dessa chave. Performance: nenhum.
**Justificativa:** Credenciais hardcoded são citadas explicitamente como exemplo CRITICAL na definição do desafio; agravado pelo fato de a ferramenta para evitar esse problema (`python-dotenv`) já estar disponível como dependência, mas não utilizada (ver H-015).

### H-002
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `app.py`
**Linha(s):** 34
**Evidência:** `app.run(debug=True, host='0.0.0.0', port=5000)` — modo debug habilitado e servidor vinculado a todas as interfaces de rede.
**Impacto:** Técnico: com debug ativo, exceções não tratadas expõem o debugger interativo do Werkzeug. Manutenção: nenhum. Testes: nenhum. Evolução: nenhum. Segurança: debugger interativo acessível pela rede é uma vulnerabilidade conhecida que pode permitir execução de código arbitrário. Performance: overhead adicional do modo debug.
**Justificativa:** Combinação de bind público com debugger interativo habilitado, configuração incompatível com um ambiente de produção.

### H-003
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `app.py`, `routes/user_routes.py`, `routes/task_routes.py`, `routes/report_routes.py` (todos os arquivos de rota)
**Linha(s):** arquivos completos — nenhuma ocorrência de verificação de autenticação/autorização encontrada
**Evidência:** Busca textual por termos associados a controle de acesso (`Authorization`, `login_required`, `require_auth`, verificação de cabeçalho/token) no projeto inteiro retorna apenas a criação do token em `routes/user_routes.py:210` — nenhuma rota (incluindo `DELETE /users/<id>`, `PUT /users/<id>` que permite alterar `role` para `admin`, `DELETE /tasks/<id>`, `DELETE /categories/<id>`) verifica identidade, papel ou token antes de executar.
**Impacto:** Técnico: qualquer requisição, de qualquer origem, pode ler, criar, alterar ou excluir qualquer recurso, incluindo promover um usuário a `admin` via `PUT /users/<id>` com `{"role": "admin"}` (`routes/user_routes.py:119-122`, sem qualquer checagem de quem está fazendo a requisição). Manutenção: nenhuma trava impede uso indevido. Testes: dificulta simular cenários de autorização, pois não existem. Evolução: qualquer nova rota herdará a ausência de proteção, salvo decisão explícita em contrário. Segurança: controle de acesso inexistente em toda a superfície da API. Performance: nenhum impacto direto.
**Justificativa:** Ausência completa de autenticação/autorização é uma violação total de separação de responsabilidades e controle de acesso, consistente com a definição CRITICAL do desafio.

### H-004
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `routes/user_routes.py`
**Linha(s):** 185-211 (rota `/login`), especificamente linha 210
**Evidência:** `'token': 'fake-jwt-token-' + str(user.id)` — o token retornado pelo login é a concatenação de um prefixo fixo com o ID numérico do usuário, sem assinatura, sem expiração e sem qualquer estrutura de JWT real, apesar do nome sugerir o contrário. O próprio seed de dados do projeto contém uma task cujo título é "Implementar autenticação JWT" com descrição "Adicionar autenticação real com JWT" (`seed.py:66`), reconhecendo implicitamente, nos próprios dados de exemplo do projeto, que a autenticação JWT real ainda não existe.
**Impacto:** Técnico: qualquer pessoa pode construir um token válido para qualquer usuário apenas conhecendo (ou adivinhando sequencialmente) seu ID — não é necessário conhecer a senha. Manutenção: um desenvolvedor lendo o nome do campo (`token`) e o prefixo (`fake-jwt-token-`) pode ser levado a acreditar que existe um JWT real sendo validado em algum lugar. Testes: nenhum impacto direto. Evolução: qualquer rota que um dia venha a "confiar" nesse token herdará uma falha de segurança grave. Segurança: token completamente forjável, sem qualquer valor de segurança real. Performance: nenhum.
**Justificativa:** Combinado com H-003 (nenhuma rota valida esse token de qualquer forma), este finding evidencia uma falha de autenticação ainda mais enganosa do que a simples ausência de login: existe a aparência de um mecanismo de autenticação, sem sua função real.

### H-005
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `models/user.py`
**Linha(s):** 27-32
**Evidência:** `set_password` aplica `hashlib.md5(pwd.encode()).hexdigest()` (linha 29) e `check_password` compara com o mesmo cálculo (linha 32) — MD5 sem qualquer salt.
**Impacto:** Técnico: MD5 é um algoritmo de hash criptograficamente quebrado para uso em senhas — rápido de calcular (permite ataques de força bruta em larga escala) e vulnerável a tabelas rainbow, especialmente sem salt (hashes idênticos para senhas idênticas entre usuários diferentes, visível inclusive nos dados de seed com senhas curtas como `'1234'`, `'abcd'`, `'pass'`, `seed.py:19,26,33`). Manutenção: qualquer decisão futura de reforçar segurança de senha exigirá migração de todos os hashes existentes. Testes: nenhum impacto direto. Evolução: qualquer novo fluxo de autenticação herdará a fragilidade. Segurança: senhas comprometíveis em caso de vazamento do banco. Performance: nenhum impacto relevante.
**Justificativa:** Uso de algoritmo de hash inadequado para proteção de senhas é uma falha de segurança grave, consistente com a definição CRITICAL do desafio ("expõem dados sensíveis") — mesmo sendo tecnicamente "um hash real", o algoritmo escolhido não oferece proteção adequada.

### H-006
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `models/user.py` (linhas 16-25) combinado com `routes/user_routes.py` (linhas 33, 209)
**Linha(s):** 16-25 (`models/user.py`); 33, 209 (`routes/user_routes.py`)
**Evidência:** `User.to_dict()` inclui `'password': self.password` (linha 21) — o hash da senha. Esse método é chamado em `get_user` (`routes/user_routes.py:33`, expondo o hash via `GET /users/<id>`) e em `login` (`routes/user_routes.py:209`, expondo o hash na própria resposta de login bem-sucedido).
**Impacto:** Técnico: o hash de senha de qualquer usuário é obtido por qualquer requisição não autenticada a `GET /users/<id>` (ver H-003). Manutenção: qualquer novo consumidor da API recebe o hash sem necessidade. Testes: nenhum impacto direto. Evolução: risco se propaga a qualquer cliente que consome esses endpoints. Segurança: exposição direta do hash de senha, que, combinado a H-005 (MD5 sem salt), facilita ataques offline de quebra de senha. Performance: nenhum.
**Justificativa:** Exposição de credenciais (mesmo hasheadas) via resposta de API é citada como CRITICAL na definição do desafio; nota-se que `GET /users` (listagem, linhas 10-25) constrói o dicionário manualmente e **não** inclui a senha — inconsistência que evidencia que a omissão em outros pontos não foi uma decisão de design deliberada, e sim um efeito colateral de usar `to_dict()` sem filtragem em alguns endpoints e montagem manual em outros.

### H-007
**Categoria:** Organização / Arquitetura
**Severidade:** MEDIUM
**Arquivo:** `services/notification_service.py`
**Linha(s):** 1-49 (arquivo completo)
**Evidência:** A classe `NotificationService`, com métodos para notificar atribuição de task (`notify_task_assigned`) e task atrasada (`notify_task_overdue`), nunca é importada nem instanciada por nenhum outro arquivo do projeto — confirmado por busca textual pelo nome da classe em todo o repositório, que retorna apenas ocorrências dentro do próprio arquivo. Nenhuma rota de criação/atualização de task (`routes/task_routes.py`) chama esses métodos, mesmo quando uma task é criada já com `user_id` atribuído (linha 131) ou quando o conceito de "overdue" é usado repetidamente em outros pontos do código (ver H-012).
**Impacto:** Técnico: a funcionalidade de notificação, embora implementada, nunca é executada em tempo de execução algum. Manutenção: um desenvolvedor pode gastar tempo entendendo/mantendo um código que não tem efeito observável no sistema. Testes: nenhum teste poderia validar um comportamento de notificação que nunca é acionado. Evolução: qualquer nova funcionalidade que assuma, pelo nome da pasta `services/`, que notificações já funcionam, estará operando sob uma premissa falsa. Segurança: nenhum impacto direto por si só (mas ver H-008). Performance: nenhum.
**Justificativa:** Existência de uma camada estrutural (pasta `services/`) que não é efetivamente utilizada pelo restante da aplicação é um problema de organização — a separação física de responsabilidades não corresponde a uma separação efetiva de responsabilidades em tempo de execução.

### H-008
**Categoria:** Segurança
**Severidade:** CRITICAL
**Arquivo:** `services/notification_service.py`
**Linha(s):** 9-10
**Evidência:** `self.email_user = 'taskmanager@gmail.com'` e `self.email_password = 'senha123'` — credencial de e-mail escrita literalmente no código-fonte, dentro da classe descrita em H-007.
**Impacto:** Técnico: qualquer pessoa com acesso ao repositório obtém a credencial de e-mail. Manutenção: rotação exige alteração de código. Testes: nenhum impacto direto. Evolução: se a classe algum dia for de fato conectada às rotas (corrigindo H-007), a credencial hardcoded seria usada em produção sem que ninguém precisasse notar o problema durante essa integração. Segurança: comprometimento potencial da conta de e-mail. Performance: nenhum.
**Justificativa:** O fato de o código nunca ser executado (H-007) não elimina o risco: a credencial já está exposta no repositório de código-fonte, que é o vetor de vazamento relevante para este tipo de falha, independentemente de o código estar "vivo" em tempo de execução.

### H-009
**Categoria:** Manutenibilidade / Organização
**Severidade:** HIGH
**Arquivo:** `utils/helpers.py`, cruzado com `routes/*.py` e `models/*.py`
**Linha(s):** 19-23 (`validate_email`), 25-29 (`sanitize_string`), 31-34 (`generate_id`), 36-41 (`log_action`), 52-55 (`is_valid_color`), 57-108 (`process_task_data`), 110-116 (constantes `VALID_STATUSES`, `VALID_ROLES`, `MAX_TITLE_LENGTH`, `MIN_TITLE_LENGTH`, `MIN_PASSWORD_LENGTH`, `DEFAULT_PRIORITY`, `DEFAULT_COLOR`)
**Evidência:** Busca textual por cada um desses 7 identificadores de função e 7 constantes em todo o repositório mostra que nenhum deles é importado ou referenciado fora do próprio arquivo `utils/helpers.py`. Adicionalmente, as 2 funções que **são** importadas em outro arquivo (`format_date`, `calculate_percentage`, importadas em `routes/report_routes.py:7`) também nunca são efetivamente chamadas em `report_routes.py` — o cálculo de porcentagem é reimplementado manualmente e inline em pelo menos 3 pontos (`routes/task_routes.py:296`, `routes/report_routes.py:67,151`) em vez de chamar `calculate_percentage`, que existe especificamente para isso.
**Impacto:** Técnico: um módulo inteiro dedicado a centralizar validação e formatação existe, mas a aplicação real não depende dele. Manutenção: qualquer alteração de regra (ex.: comprimento mínimo de senha) precisa ser localizada e alterada nos pontos onde a lógica foi duplicada manualmente, e não no único lugar aparentemente destinado a isso. Testes: um teste unitário escrito contra `utils/helpers.py` não validaria o comportamento real da aplicação, pois as rotas não usam essas funções. Evolução: aumenta a divergência ao longo do tempo entre o "utilitário disponível" e o "comportamento real implementado". Segurança: nenhum impacto direto adicional. Performance: nenhum.
**Justificativa:** Diferente de duplicação de código comum (onde não havia lugar centralizado), aqui existe um local corretamente projetado para centralizar a lógica, e mesmo assim ele não é utilizado — uma forma mais grave de violação do princípio DRY, pois a "dificuldade de manutenção e testes" citada na definição HIGH do desafio se aplica tanto ao código morto quanto às duplicações que ele deveria ter evitado.

### H-010
**Categoria:** Code Smell (Duplicate Code)
**Severidade:** MEDIUM
**Arquivo:** `routes/user_routes.py`
**Linha(s):** 61, 106 (comparadas a `utils/helpers.py:19-23`)
**Evidência:** A expressão regular `r'^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$'` é escrita literalmente duas vezes em `user_routes.py` (linha 61, na criação de usuário; linha 106, na atualização), em vez de chamar `validate_email()`, já definida em `utils/helpers.py:19-23` com a mesma expressão regular exata.
**Impacto:** Técnico: nenhum em runtime. Manutenção: qualquer ajuste na regra de validação de e-mail exige localizar e alterar dois pontos idênticos dentro do mesmo arquivo, além de um terceiro ponto (a função não utilizada) que aparentaria ser o lugar "certo" para a mudança. Testes: duplica a superfície de testes necessária para o mesmo comportamento. Evolução: aumenta o risco de divergência entre os dois pontos ao longo do tempo. Segurança: nenhum impacto direto. Performance: nenhum.
**Justificativa:** Duplicação de código é citada explicitamente como exemplo de severidade MEDIUM na definição do desafio, agravada aqui pela existência de uma função equivalente já pronta e não utilizada (ver H-009).

### H-011
**Categoria:** Code Smell (Magic Numbers)
**Severidade:** LOW
**Arquivo:** `routes/user_routes.py`
**Linha(s):** 64, 115 (comparadas a `utils/helpers.py:114`)
**Evidência:** `if len(password) < 4:` é escrito literalmente duas vezes (linha 64, criação; linha 115, atualização), em vez de referenciar a constante `MIN_PASSWORD_LENGTH = 4`, já definida em `utils/helpers.py:114`.
**Impacto:** Técnico: nenhum em runtime. Manutenção: um leitor não sabe, sem contexto adicional, se o valor `4` é arbitrário ou uma decisão de negócio documentada em algum lugar (na verdade está documentado — na constante não utilizada). Testes: nenhum impacto direto. Evolução: qualquer ajuste dessa regra de negócio exige localizar os literais espalhados. Segurança: nenhum. Performance: nenhum.
**Justificativa:** Magic numbers são citados explicitamente como exemplo de severidade LOW na definição do desafio.

### H-012
**Categoria:** Code Smell (Duplicate Code) / SOLID
**Severidade:** HIGH
**Arquivo:** `models/task.py` (linhas 50-60, método `is_overdue`), `routes/task_routes.py` (linhas 30-39, 71-80), `routes/user_routes.py` (linhas 171-180), `routes/report_routes.py` (linhas 34-37, 132-135)
**Linha(s):** 50-60 (`models/task.py`); 30-39, 71-80 (`routes/task_routes.py`); 171-180 (`routes/user_routes.py`); 34-37, 132-135 (`routes/report_routes.py`)
**Evidência:** `Task.is_overdue()` (`models/task.py:50-60`) encapsula corretamente a regra "task com `due_date` no passado e status diferente de `done`/`cancelled`". A mesma sequência de condicionais aninhados (`if due_date: if due_date < now: if status not in (done, cancelled): ...`) é reimplementada manualmente, de forma equivalente, em pelo menos 5 outros pontos do código, nenhum dos quais chama `task.is_overdue()`.
**Impacto:** Técnico: nenhum erro em runtime — cada reimplementação produz o resultado correto isoladamente. Manutenção: qualquer mudança futura na definição de "atrasada" (ex.: adicionar um novo status que também conta como concluído) exigiria alterar 6 lugares (o método e as 5 reimplementações) para permanecer consistente — esquecer um deles introduziria uma divergência silenciosa de comportamento entre endpoints. Testes: um teste unitário para `Task.is_overdue()` não cobriria o comportamento das 5 reimplementações paralelas. Evolução: cada novo endpoint que precisar dessa informação tende a criar uma sexta reimplementação, seguindo o padrão já estabelecido no restante do código. Segurança: nenhum impacto direto. Performance: nenhum.
**Justificativa:** Viola o princípio DRY de forma mais grave que uma duplicação comum, pois a abstração correta já existe e está disponível — o problema não é ausência de um lugar para centralizar a lógica, mas a não utilização do lugar que já existe, o que caracteriza também uma violação do propósito do encapsulamento do Model no MVC (a lógica de domínio deveria "morar" no Model e ser reutilizada, não replicada).

### H-013
**Categoria:** Performance
**Severidade:** MEDIUM
**Arquivo:** `routes/task_routes.py` (linhas 11-63), `routes/report_routes.py` (linhas 53-68)
**Linha(s):** 11-63 (`routes/task_routes.py`); 53-68 (`routes/report_routes.py`)
**Evidência:** Em `get_tasks` (`task_routes.py`), para cada task retornada por `Task.query.all()` (linha 14), o código executa uma nova consulta `User.query.get(t.user_id)` (linha 42) e `Category.query.get(t.category_id)` (linha 51) dentro do laço. Em `summary_report` (`report_routes.py`), para cada usuário retornado por `User.query.all()` (linha 53), o código executa uma nova consulta `Task.query.filter_by(user_id=u.id).all()` (linha 56) dentro do laço.
**Impacto:** Técnico: o número de consultas cresce proporcionalmente ao volume de tasks/usuários, em vez de usar uma consulta agregada ou `join`/`joinedload` do próprio SQLAlchemy (disponível na ferramenta já utilizada pelo projeto). Manutenção: nenhum impacto direto. Testes: nenhum impacto direto. Evolução: piora proporcionalmente ao crescimento da base. Segurança: nenhum. Performance: degradação perceptível com o crescimento do volume de dados.
**Justificativa:** Consultas N+1 são citadas explicitamente como exemplo de severidade MEDIUM na definição do desafio; a manifestação aqui usa a API do ORM (`.query.get()` dentro de um laço) em vez de SQL cru, mas o padrão estrutural é o mesmo de um N+1 clássico.

### H-014
**Categoria:** Organização
**Severidade:** MEDIUM
**Arquivo:** `requirements.txt` (linha 4), cruzado com todo o código-fonte
**Linha(s):** 4
**Evidência:** `marshmallow==3.20.1` está declarada como dependência do projeto, mas nenhuma ocorrência de `import marshmallow` ou de `Schema` (padrão de uso típico da biblioteca) foi encontrada em nenhum arquivo `.py` do projeto. Toda a validação de entrada observada (`routes/user_routes.py`, `routes/task_routes.py`, `routes/report_routes.py`) é feita manualmente, com condicionais inline, incluindo a reimplementação parcial do que `utils/helpers.py:process_task_data` (também não utilizada, ver H-009) já tentava centralizar.
**Impacto:** Técnico: nenhum em runtime. Manutenção: a intenção aparente do projeto (usar uma biblioteca de schema para centralizar validação/serialização) não se concretiza, e o time mantém validação manual duplicada e dispersa. Testes: dificulta testar regras de validação de forma isolada e declarativa. Evolução: qualquer nova entidade tende a repetir o mesmo padrão de validação manual. Segurança: nenhum impacto direto adicional (mas contribui para inconsistências como H-017). Performance: nenhum.
**Justificativa:** A presença de uma dependência de validação instalada e nunca utilizada é um sinal concreto de intenção arquitetural não realizada, relevante para avaliar organização e maturidade do projeto além da simples contagem de pastas.

### H-015
**Categoria:** Organização
**Severidade:** MEDIUM
**Arquivo:** `requirements.txt` (linha 6), cruzado com `app.py`
**Linha(s):** 6
**Evidência:** `python-dotenv==1.0.0` está declarada como dependência, mas nenhuma ocorrência de `import dotenv` ou `load_dotenv` foi encontrada em nenhum arquivo do projeto — a configuração (`SECRET_KEY`, URI do banco) permanece hardcoded em `app.py:11-13` (ver H-001).
**Impacto:** Técnico: nenhum em runtime. Manutenção: mesmo tendo a ferramenta correta disponível para resolver H-001, o problema persiste. Testes: nenhum impacto direto. Evolução: qualquer novo valor de configuração sensível tende a ser adicionado da mesma forma hardcoded, seguindo o padrão já estabelecido. Segurança: contribui indiretamente para H-001 ao mostrar que a causa não é falta de ferramenta disponível. Performance: nenhum.
**Justificativa:** Mesma fundamentação de H-014 — dependência instalada e não utilizada é evidência concreta de intenção arquitetural não realizada.

### H-016
**Categoria:** Segurança / Manutenibilidade
**Severidade:** MEDIUM
**Arquivo:** `routes/task_routes.py` (linhas 62-63), `routes/report_routes.py` (linhas 186-188, 207-209, 221-223)
**Linha(s):** 62-63 (`routes/task_routes.py`); 186-188, 207-209, 221-223 (`routes/report_routes.py`)
**Evidência:** `get_tasks` usa `except:` sem tipo especificado (linha 62), retornando apenas `{'error': 'Erro interno'}` (linha 63); `create_category`, `update_category` e `delete_category` fazem o mesmo (linhas 186, 207, 221), sem capturar ou logar a exceção original.
**Impacto:** Técnico: qualquer erro (incluindo erros de programação não relacionados ao banco) é silenciosamente convertido em uma resposta genérica, sem nenhum registro (`print` ou log) do que de fato ocorreu — diferente de outras rotas do mesmo projeto que usam `except Exception as e:` com `print(f"ERRO: {str(e)}")` (ex.: `user_routes.py:87-89`). Manutenção: diagnosticar falhas nesses 4 pontos específicos é significativamente mais difícil do que nos demais, pois não há rastro do erro real. Testes: nenhum teste pode validar o comportamento esperado para um erro específico, pois nenhum é diferenciado. Evolução: qualquer novo bug introduzido nessas funções falha silenciosamente. Segurança: nenhum impacto direto relevante (o erro não é exposto ao cliente, apenas descartado). Performance: nenhum.
**Justificativa:** Tratamento de erro incorreto é citado como exemplo de severidade MEDIUM na definição do desafio; a inconsistência entre `except:` bare e `except Exception as e:` dentro do mesmo projeto (às vezes no mesmo arquivo) é evidência adicional de falta de um padrão único de tratamento de erro.

### H-017
**Categoria:** Manutenibilidade / Validação
**Severidade:** MEDIUM
**Arquivo:** `routes/report_routes.py`
**Linha(s):** 190-202 (`update_category`), comparadas a 167-171 (`create_category`)
**Evidência:** `create_category` verifica `if not data: return jsonify({'error': 'Dados inválidos'}), 400` (linhas 170-171) antes de acessar `data.get(...)`. `update_category` (linhas 196-202) acessa diretamente `'name' in data`, `'description' in data`, `'color' in data` **sem** essa mesma checagem prévia de `data` ser `None`.
**Impacto:** Técnico: uma requisição `PUT /categories/<id>` sem corpo JSON válido (`data` sendo `None`) causaria uma exceção não tratada na expressão `'name' in data` (operação inválida sobre `None`), antes mesmo de chegar ao bloco `try/except` que só envolve a parte de persistência (linhas 204-209) — evidência de que o tratamento de erro desta função não cobre essa validação específica. Manutenção: inconsistência entre duas rotas irmãs (criar/atualizar da mesma entidade) que deveriam seguir o mesmo padrão de validação. Testes: nenhum teste no repositório cobre esse cenário. Evolução: qualquer nova rota copiada a partir de `update_category` como referência herdaria a mesma omissão. Segurança: nenhum impacto direto relevante. Performance: nenhum.
**Justificativa:** Validação inconsistente entre rotas que operam sobre a mesma entidade é citada como exemplo de severidade MEDIUM na definição do desafio ("validações ausentes nas rotas").

### H-018
**Categoria:** Arquitetura / Manutenibilidade
**Severidade:** LOW
**Arquivo:** `app.py`
**Linha(s):** 30-31 (comparadas a 33-34)
**Evidência:** `with app.app_context(): db.create_all()` (linhas 30-31) está no nível superior do módulo, fora do bloco `if __name__ == '__main__':` (linhas 33-34) — é executado sempre que `app.py` é importado por qualquer outro script, incluindo `seed.py:2` (`from app import app, db`).
**Impacto:** Técnico: qualquer script que precise apenas de partes de `app.py` (ex.: a instância `app` para configurar testes) aciona, como efeito colateral da importação, a criação do schema do banco. Manutenção: acopla a simples importação do módulo de entrada a uma operação de infraestrutura. Testes: dificulta escrever testes que importem seletivamente partes da aplicação sem também inicializar o banco completo. Evolução: qualquer novo script auxiliar que importe `app.py` herda esse efeito colateral. Segurança: nenhum impacto direto relevante. Performance: nenhum impacto relevante neste volume.
**Justificativa:** Código executável fora de um guard de execução explícito é um problema de organização do ponto de entrada, reduzindo a previsibilidade de módulos importáveis — relevante para os critérios de legibilidade/organização citados na definição do desafio.

### H-019
**Categoria:** Manutenibilidade
**Severidade:** LOW
**Arquivo:** `models/user.py`
**Linha(s):** 34-38
**Evidência:** `is_admin` é implementado como `if self.role == 'admin': return True else: return False`, em vez de uma expressão booleana direta equivalente.
**Impacto:** Técnico: nenhum em runtime — o comportamento é idêntico a uma implementação mais direta. Manutenção: adiciona verbosidade desnecessária, reduzindo levemente a legibilidade. Testes: nenhum impacto direto. Evolução: nenhum. Segurança: nenhum. Performance: nenhum.
**Justificativa:** Estilo de código desnecessariamente verboso é um problema de legibilidade, consistente com os critérios de manutenibilidade citados na definição do desafio; classificado como LOW por ter impacto estritamente estético/estilístico, sem qualquer risco funcional.

### H-020
**Categoria:** Segurança
**Severidade:** MEDIUM
**Arquivo:** `app.py`
**Linha(s):** 15
**Evidência:** `CORS(app)` é chamado sem qualquer parâmetro de restrição de origem, método ou cabeçalho, liberando requisições cross-origin de qualquer domínio para toda a API.
**Impacto:** Técnico: qualquer página web, hospedada em qualquer domínio, pode fazer requisições à API a partir do navegador de um usuário autenticado (ou não) sem restrição de origem. Manutenção: nenhuma configuração centralizada de origens permitidas existe para ser ajustada. Testes: nenhum impacto direto. Evolução: qualquer novo endpoint sensível herda automaticamente essa política aberta. Segurança: amplia a superfície de exposição de todos os demais problemas já identificados (especialmente H-003, ausência de autenticação) a partir de qualquer origem web. Performance: nenhum.
**Justificativa:** CORS irrestrito combinado com ausência total de autenticação amplia significativamente a superfície de exploração a partir de contextos de navegador; tratado como MEDIUM por ser, isoladamente, uma configuração permissiva (não uma falha de exposição direta de dados), mas relevante o suficiente para registro por padronização/segurança de configuração.

---

## 5. Architectural Assessment

**Principais pontos fortes:** o código está de fato dividido por domínio e por camada técnica (`models/`, `routes/`, `services/`, `utils/`), diferente de um projeto totalmente plano; todo o acesso a dados observado usa o ORM SQLAlchemy com parâmetros geridos pela própria ferramenta, sem nenhuma ocorrência de SQL cru concatenado; o schema declara corretamente chaves estrangeiras via `db.ForeignKey` para as relações `Task→User` e `Task→Category`; a camada de `models/` já contém métodos de domínio próprios (`is_overdue`, `validate_status`, `validate_priority`, `set_password`/`check_password`), ausentes em um projeto sem qualquer Model.

**Principais problemas:** ausência completa de autenticação/autorização em toda a superfície da API, incluindo uma rota que altera o papel (`role`) de um usuário para `admin` (H-003), agravada pela existência de um fluxo de login que emite um token que nunca é validado por nenhuma outra rota (H-004); senha protegida com MD5 sem salt, um algoritmo de hash real porém inadequado para esse uso (H-005); hash de senha exposto em duas respostas de API distintas (H-006); credenciais de e-mail hardcoded dentro de uma classe de serviço nunca executada (H-008); uma camada de serviço (`NotificationService`) e a maior parte de uma camada de utilitários (`utils/helpers.py`) inteiramente não conectadas ao fluxo real da aplicação (H-007, H-009); um método de Model corretamente implementado (`Task.is_overdue()`) sendo ignorado e reimplementado manualmente em pelo menos 5 outros pontos do código (H-012); duas dependências de validação/configuração (`marshmallow`, `python-dotenv`) instaladas e nunca utilizadas (H-014, H-015).

**Nível de organização:** intermediário. Existe separação física de camadas por responsabilidade técnica, mas a leitura do fluxo real de execução (a partir dos pontos de entrada — rotas e `app.py`) mostra que partes significativas dessa estrutura (uma classe de serviço inteira, a maior parte dos utilitários, uma dependência de validação) não são efetivamente utilizadas, e que a lógica de negócio corretamente encapsulada em um Model ainda vaza e se duplica nas rotas.

**Maturidade arquitetural:** parcial. A presença de pastas/módulos dedicados por responsabilidade técnica não deve ser interpretada, isoladamente, como evidência de boa separação de responsabilidades: a ausência de um único arquivo "gigante" concentrando tudo (diferente de um God Class/God Module clássico) é uma condição necessária, mas não suficiente, para uma arquitetura efetivamente bem separada — este projeto demonstra que a mesma falha de fundo (responsabilidades não isoladas de forma efetiva) pode se manifestar de formas estruturalmente diferentes: camadas presentes mas nunca alcançadas em tempo de execução, e abstrações corretas que existem mas são ignoradas pelo restante do código.

---

## 6. Project-Specific Characteristics

- O projeto distribui o código em pacotes por responsabilidade técnica (`models/`, `routes/`, `services/`, `utils/`), diferente de uma estrutura totalmente plana — mas essa divisão física nem sempre corresponde a uma separação efetiva de responsabilidades em tempo de execução, como evidenciado pelos itens abaixo.
- **Camada estrutural morta / abstração não utilizada:** módulos, classes, funções ou constantes cuja finalidade é centralizar uma responsabilidade (validação, notificação, formatação, configuração) existem no projeto, mas nunca são efetivamente importados/invocados pelo restante da aplicação a partir de seus pontos de entrada reais. Evidências: `NotificationService` nunca instanciada (H-007); 7 das 9 funções e todas as 7 constantes de `utils/helpers.py` nunca referenciadas fora do próprio arquivo, e as 2 funções que chegam a ser importadas (`format_date`, `calculate_percentage`) também não são chamadas (H-009); `marshmallow` instalado e nunca importado (H-014); `python-dotenv` instalado e nunca importado (H-015). Esse padrão só é observável porque o projeto já possui alguma divisão em módulos/camadas — cria uma falsa impressão de boa arquitetura, enquanto a lógica real diverge e se duplica nas camadas efetivamente executadas.
- **Autenticação decorativa:** existe um fluxo de login (`POST /login`) que emite um token (`'fake-jwt-token-' + str(user.id)`, H-004), mas nenhuma outra rota da aplicação de fato valida esse token (H-003) — a aparência de um mecanismo de segurança está presente, sem sua função real. Isso é mais enganoso do que a ausência total de um endpoint de login, pois um leitor pode assumir, incorretamente, que existe controle de acesso.
- **Reimplementação paralela ignorando abstração existente:** `Task.is_overdue()` (`models/task.py:50-60`) é um método de Model corretamente implementado, mas a mesma lógica é reimplementada manualmente em pelo menos 5 outros pontos do código, nenhum dos quais chama o método (H-012) — diferente de duplicação de código simples (onde nunca houve um lugar central para a lógica), aqui a abstração correta já existe e é ignorada, sinalizando falha de disciplina de reuso mesmo quando a estrutura correta está disponível.
- **Efeito colateral de inicialização no nível de módulo:** a criação do schema do banco (`db.create_all()`) ocorre no nível superior de `app.py`, fora de qualquer guard de execução, e é disparada automaticamente sempre que o módulo é importado — inclusive por `seed.py`, que apenas precisa da instância `app`/`db` (H-018).
- A camada de acesso a dados usa consistentemente o ORM SQLAlchemy, sem nenhuma ocorrência de SQL cru concatenado — diferente de um cenário de SQL Injection sistêmico, os riscos de segurança predominantes deste projeto estão concentrados em autenticação, gestão de credenciais e configuração, não em injeção de SQL.
- O schema declara corretamente chaves estrangeiras (`db.ForeignKey('users.id')`, `db.ForeignKey('categories.id')`) via SQLAlchemy — diferente de um schema sem qualquer integridade referencial declarada.
- Consultas N+1 se manifestam aqui através de chamadas do ORM dentro de laços (`Model.query.get()`/`filter_by()` repetidos por iteração), e não através de SQL cru concatenado dentro de um laço.
- O projeto tem uma quantidade de validação de entrada mais substancial do que um projeto totalmente desestruturado (formato de e-mail, tamanho mínimo de senha, unicidade de e-mail, faixa de prioridade, formato de data), mas ainda falha por inconsistência entre rotas irmãs (H-017) e por não usar a camada de validação centralizada disponível (H-009/H-014).

---

## 7. Key Learnings

- O código-fonte relevante do projeto (`app.py`, `database.py`, `seed.py`, `requirements.txt`, `models/*.py`, `routes/*.py`, `services/*.py`, `utils/*.py`) foi lido em sua totalidade, permitindo alto nível de confiança nos findings reportados, cada um apoiado por evidência direta de arquivo e linha.
- A confirmação de que uma camada (`services/`, partes de `utils/`) está efetivamente desconectada do fluxo de execução real exigiu busca textual por referência de cada identificador em todo o repositório — a mera existência de uma pasta com nome apropriado (ex.: `services/`) não é, por si só, evidência de que a funcionalidade correspondente está ativa; ausência de boa arquitetura não deve ser assumida a partir da presença de pastas, e presença de boa arquitetura tampouco deve ser assumida a partir da mesma evidência estrutural.
- A confirmação de que uma abstração correta (`Task.is_overdue()`) é ignorada exigiu localizar e comparar, ponto a ponto, cada reimplementação manual equivalente espalhada pelo código — não bastou constatar que o método existe; foi necessário verificar se ele é de fato chamado.
- A ausência de um God Class/God Module clássico neste projeto não foi, por si só, tratada como prova de boa separação de responsabilidades — a leitura aprofundada do fluxo de execução revelou formas "disfarçadas" do mesmo problema de fundo (camadas presentes mas não utilizadas, lógica duplicada ignorando abstrações já existentes).
- A distinção entre "existe validação" e "a validação é consistente e centralizada" foi relevante para avaliar corretamente H-017: este projeto tem substancialmente mais validação que um projeto sem nenhuma, mas ainda apresenta inconsistência entre rotas equivalentes sobre a mesma entidade.
- Não foi possível confirmar, apenas pela leitura do código-fonte, se as rotas estão protegidas por alguma camada externa não representada no repositório (proxy reverso, firewall, rede privada) — a ausência de proteção observada é estritamente sobre o código da aplicação em si.
- A verificação de que duas dependências declaradas (`marshmallow`, `python-dotenv`) não são utilizadas exigiu cruzar o conteúdo de `requirements.txt` com uma busca textual pelos padrões de uso típicos de cada biblioteca (`import marshmallow`/`Schema`; `import dotenv`/`load_dotenv`) em todos os arquivos `.py` do projeto.

---

## 8. Considerations for the Future Skill

- A ausência de um arquivo/classe "gigante" concentrando múltiplas responsabilidades não deve, isoladamente, ser interpretada como evidência de boa separação de responsabilidades — este projeto demonstra que a mesma falha de fundo pode se manifestar de forma estruturalmente diferente (camadas presentes mas nunca alcançadas em tempo de execução; abstrações corretas que existem mas são ignoradas), exigindo heurísticas que vão além de detectar um único arquivo grande.
- A verificação de que uma camada/módulo é efetivamente utilizado exige uma busca real de referências (alcançabilidade) a partir dos pontos de entrada da aplicação — a existência de uma pasta com nome apropriado (`services/`, `utils/`) não deve ser tratada como evidência de uso, nem sua ausência como evidência de má organização, sem essa verificação.
- A qualidade de um mecanismo de proteção (ex.: hashing de senha, autenticação) precisa ser avaliada além de sua mera presença — este projeto usa uma função de hash criptográfico real (`hashlib.md5`), mas de um algoritmo inadequado e sem salt, e um fluxo de login que emite um token nunca validado por nenhuma outra rota. Detectar apenas "existe uma chamada de hashing" ou "existe uma rota de login" seria insuficiente para captar essas falhas.
- Consultas N+1 podem se manifestar tanto por concatenação de SQL cru dentro de um laço quanto por chamadas de ORM (`Model.query.get()`/`filter_by()`) dentro de um laço — a detecção precisa reconhecer ambas as formas sintáticas do mesmo padrão estrutural.
- A existência de dependências declaradas em um arquivo de manifesto (`requirements.txt`) mas nunca importadas no código é um sinal concreto e verificável de intenção arquitetural não realizada, relevante para avaliar a maturidade real de um projeto além da leitura de sua estrutura de pastas.
- A reimplementação manual de uma regra já encapsulada corretamente em um método de Model é uma falha de disciplina de reuso distinta de uma duplicação de código comum (onde nunca existiu um lugar central) — vale a pena tratar como uma categoria própria de achado, já que a causa raiz (e portanto a correção necessária) é diferente.
- Um efeito colateral de inicialização (ex.: criação de schema de banco) executado no nível superior de um módulo, fora de qualquer guard de execução, é um sinal observável relacionado a como o ponto de entrada da aplicação está estruturado, relevante para linguagens com módulos diretamente importáveis que executam código ao serem carregados.
