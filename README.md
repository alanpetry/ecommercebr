# E-commerce BR

Wiki pública e indexável das conversas da pasta **E-commerce** do Telegram.

O site é estático e pronto para GitHub Pages. As mensagens passam por sanitização antes da publicação:

- links são removidos;
- e-mails e telefones são removidos;
- mensagens promocionais, spam e divulgação são ignoradas;
- autores são exibidos por `@username` quando existir, ou apenas primeiro nome.

## Estrutura

- `config/site.json`: nome, descrição, URL pública e nome da pasta do Telegram.
- `config/groups.json`: metadados editáveis dos grupos. Use este arquivo para renomear grupos, ajustar slug, descrição e avatar sem mexer nos dados brutos.
- `config/tags.json`: palavras-chave usadas para taguear mensagens.
- `content/messages/*.jsonl`: mensagens sanitizadas por grupo.
- `content/media/groups`: fotos atuais dos grupos.
- `docs`: site estático gerado para GitHub Pages.
- `scripts/sync_telegram.py`: sincroniza a pasta E-commerce via Telethon.
- `scripts/build_site.py`: gera o site.
- `scripts/daily_update.sh`: sincroniza, gera, commita e publica.

## Rodar localmente

```bash
../.venv/bin/python scripts/sync_telegram.py
../.venv/bin/python scripts/build_site.py
python3 -m http.server 8080 --directory docs
```

Depois acesse `http://localhost:8080`.

## Publicação diária

Use:

```bash
cd /Users/alanpetry/Desktop/Telegram/ecommercebr
./scripts/daily_update.sh
```

## Segurança editorial

O filtro é conservador. Se uma mensagem tiver telefone, e-mail ou parecer divulgação, ela não entra no site. Links são removidos do texto antes de publicar.

