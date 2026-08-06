# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

A aplicação sobe em `http://localhost:5000`. O `app.py` na raiz é um shim que delega para `src/app.py` — a estrutura interna mudou, mas o comando de subir continua o mesmo. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo (senhas já armazenadas com hash).

### Variáveis de ambiente (opcionais)

| Variável | Padrão | Uso |
|---|---|---|
| `FLASK_HOST` | `0.0.0.0` | Endereço em que o servidor escuta |
| `FLASK_PORT` | `5000` | Porta do servidor — troque se a 5000 já estiver em uso (no macOS, o AirPlay Receiver costuma ocupá-la) |
| `FLASK_DEBUG` | `false` | Ativa o modo debug do Flask |
| `SECRET_KEY` | valor de desenvolvimento | Chave de sessão do Flask |
| `DB_PATH` | `loja.db` | Caminho do arquivo SQLite |
| `ADMIN_TOKEN` | valor de desenvolvimento | Token exigido no header `X-Admin-Token` para acessar `/admin/reset-db` e `/admin/query` |

Exemplo subindo em outra porta e com um token de admin próprio:

```bash
ADMIN_TOKEN=meu-token-secreto FLASK_PORT=5050 .venv/bin/python app.py
```
