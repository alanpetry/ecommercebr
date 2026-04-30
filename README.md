# E-commerce BR

Wiki pública e indexável das conversas da pasta **E-commerce** do Telegram.

O site é estático e pronto para GitHub Pages. As mensagens passam por sanitização e moderação antes da publicação:

- links de mensagens são ocultados como `[link oculto]`;
- e-mails e telefones são removidos por privacidade;
- mensagens promocionais, spam e divulgação são avaliadas por IA via Codex CLI antes de publicar;
- autores são exibidos por `@username` quando existir, ou apenas primeiro nome.

## Estrutura

- `config/site.json`: nome, descrição, URL pública e nome da pasta do Telegram.
- `config/groups.json`: metadados editáveis dos grupos. Use este arquivo para renomear grupos, ajustar slug, descrição e avatar sem mexer nos dados brutos.
- `config/moderation.json`: rejeições manuais retroativas e configuração editorial.
- `config/tags.json`: palavras-chave usadas para taguear mensagens.
- `content/messages/*.jsonl`: mensagens sanitizadas por grupo.
- `content/media/groups`: fotos atuais dos grupos.
- `docs`: site estático gerado para GitHub Pages.
- `scripts/sync_telegram.py`: sincroniza a pasta E-commerce via Telethon.
- `scripts/ai_moderate.py`: usa IA para decidir caso a caso se uma mensagem é publicação legítima ou propaganda/spam.
- `scripts/build_site.py`: gera o site.
- `scripts/daily_update.sh`: sincroniza, gera, commita e publica.

## Rodar localmente

```bash
../.venv/bin/python scripts/sync_telegram.py
../.venv/bin/python scripts/clean_content.py
../.venv/bin/python scripts/ai_moderate.py
../.venv/bin/python scripts/build_site.py
../.venv/bin/python scripts/preview_site.py --port 8080
```

Depois acesse `http://localhost:8080/ecommercebr/`.

## Publicação diária

Use:

```bash
cd /Users/alanpetry/Desktop/Telegram/ecommercebr
./scripts/daily_update.sh
```

## Segurança editorial

O filtro automático não decide spam por regex de palavras-chave. Telefones e e-mails são bloqueados por privacidade, links são ocultados, e a decisão editorial de propaganda/spam é feita por IA. Se a IA não estiver disponível, o update diário falha para evitar publicar mensagens sem revisão.

## Domínio próprio

O GitHub Pages padrão continua em `https://alanpetry.github.io/ecommercebr/`. Para remover `alanpetry` do domínio, configure um domínio próprio no GitHub Pages e no DNS. Depois disso, atualize `base_url` e `base_path` em `config/site.json`, gere novamente o site e use um arquivo `docs/CNAME` com o domínio.
