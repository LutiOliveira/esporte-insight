# Deploy — Esporte Insight

> Copa 2026 começa em **11 de junho de 2026**. Siga os passos abaixo para
> ter o site no ar antes disso.

---

## Opção A — Render.com (recomendado, mais simples)

### Custo
| Plano | Preço | Problema |
|-------|-------|---------|
| Free | Grátis | Hiberna após 15 min de inatividade — ruim para Copa |
| **Starter** | **US$ 7/mês** | **Sempre ativo — use esse durante a Copa** |

---

### Passo 1 — Suba o código no GitHub

```bash
# No terminal, dentro da pasta copa_insight:
git init
git add .
git commit -m "feat: Esporte Insight v1"

# Crie um repositório no github.com (pode ser privado) e siga as instruções
git remote add origin https://github.com/SEU_USUARIO/esporte-insight.git
git push -u origin main
```

> ⚠️ O `.gitignore` já exclui `.env` e `copa.db`. Nunca suba sua API key!

---

### Passo 2 — Criar conta no Render

1. Acesse **render.com** e crie uma conta gratuita (pode usar o GitHub)
2. Clique em **New → Blueprint**
3. Conecte seu repositório GitHub
4. O Render vai detectar o `render.yaml` automaticamente

---

### Passo 3 — Configurar variáveis de ambiente

No painel do Render, vá em **Environment** e adicione:

| Variável | Valor |
|----------|-------|
| `ODDS_API_KEY` | `244a718afdf6800231deac02523d2524` |
| `SECRET_KEY` | (gerado automaticamente pelo render.yaml) |
| `TELEGRAM_BOT_TOKEN` | (opcional — só se quiser o bot) |

---

### Passo 4 — Ativar disco persistente

O `render.yaml` já configura o disco. Confirme que aparece:
- **Disk**: `esporte-insight-data` → `/opt/render/project/src/data` → 1 GB

Isso garante que o banco de dados SQLite **não é apagado** entre deploys.

---

### Passo 5 — Deploy!

Clique em **Apply** e aguarde ~3 minutos. Seu site estará em:
```
https://esporte-insight.onrender.com
```

---

## Opção B — Docker (VPS próprio / DigitalOcean / Coolify)

Se preferir ter controle total com um VPS (DigitalOcean Droplet a partir de
US$ 6/mês):

```bash
# No servidor:
git clone https://github.com/SEU_USUARIO/esporte-insight.git
cd esporte-insight

# Crie o .env com as variáveis
cp .env.example .env
nano .env   # adicione ODDS_API_KEY e SECRET_KEY

# Build e execução
docker build -t esporte-insight .
docker run -d \
  --name esporte-insight \
  -p 80:8000 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  --restart unless-stopped \
  esporte-insight
```

---

## Domínio personalizado (opcional)

Para usar `esporteinsight.com.br` em vez da URL do Render:

1. Compre o domínio no **Registro.br** (~R$ 40/ano para `.com.br`)
2. No Render → **Settings → Custom Domains** → adicione o domínio
3. Copie o CNAME fornecido e configure no DNS do seu provedor

---

## Telegram Bot (para alertas)

1. No Telegram, procure por **@BotFather**
2. Envie `/newbot` e siga as instruções
3. Copie o token gerado (ex: `7123456789:AAG...`)
4. Adicione como variável `TELEGRAM_BOT_TOKEN` no Render
5. Configure o webhook (substitua pela sua URL):

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://esporte-insight.onrender.com/api/telegram/webhook"
```

6. Usuários se inscrevem enviando `/start` para o seu bot

---

## Monitoramento após o deploy

- **Saúde da API**: `GET /api/quota` → mostra requests restantes
- **Logs**: Render → **Logs** em tempo real
- **Atualização manual**: `POST /api/refresh` → força fetch de odds

---

## Checklist pré-Copa (antes de 11/06)

- [ ] Repositório GitHub criado
- [ ] Deploy no Render funcionando
- [ ] Variável `ODDS_API_KEY` configurada
- [ ] Domínio personalizado (opcional)
- [ ] Telegram Bot configurado (opcional)
- [ ] Plano Starter ativo (para não hibernar durante os jogos)
- [ ] Testar aba Grupos, Chaveamento e Apostas de Valor
