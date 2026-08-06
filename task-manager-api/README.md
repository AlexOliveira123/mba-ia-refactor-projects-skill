# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`. Diferente dos outros projetos, este já possui alguma separação de camadas (`models/`, `routes/`, `services/`, `utils/`), mas ainda contém problemas arquiteturais e de qualidade.

## Como rodar

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python seed.py
.venv/bin/python app.py
```

A aplicação sobe em `http://localhost:5000`. O `seed.py` popula o banco SQLite (`tasks.db`) com usuários, categorias e tasks de exemplo — **rode-o antes do primeiro boot**, caso contrário os endpoints vão retornar listas vazias.

### Variáveis de ambiente (opcionais)

| Variável | Padrão | Uso |
|---|---|---|
| `FLASK_HOST` | `0.0.0.0` | Endereço em que o servidor escuta |
| `FLASK_PORT` | `5000` | Porta do servidor — troque se a 5000 já estiver em uso (no macOS, o AirPlay Receiver costuma ocupá-la) |
| `FLASK_DEBUG` | `false` | Ativa o modo debug do Flask |
| `SECRET_KEY` | valor de desenvolvimento | Usada para assinar o token de login |
| `DATABASE_URL` | `sqlite:///tasks.db` | URI do banco (SQLAlchemy) |
| `CORS_ORIGINS` | `http://localhost:3000` | Lista de origens permitidas (separadas por vírgula) |

### Autenticação

`POST /login` retorna um token assinado (`itsdangerous`), exigido via header `Authorization: Bearer <token>` em:

- `DELETE /tasks/<id>`, `DELETE /users/<id>`, `DELETE /categories/<id>` — qualquer usuário autenticado.
- `PUT /users/<id>` ao alterar `role` — exige que quem chama já seja `admin`; caso contrário retorna `403`.

Todas as demais rotas (leituras, criação/edição de tasks e categorias, campos não sensíveis de usuário) continuam públicas, como no projeto original.

Exemplo:

```bash
TOKEN=$(curl -s -X POST http://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"email":"joao@email.com","password":"1234"}' | python3 -c "import json,sys; print(json.load(sys.stdin)['token'])")

curl -X DELETE http://localhost:5000/tasks/1 -H "Authorization: Bearer $TOKEN"
```
