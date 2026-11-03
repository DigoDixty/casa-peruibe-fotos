# 📋 Diário de Bordo & Guia de Migração: Organizador de Fotos Casa Peruíbe

> **Destino da Migração:** `dixty_office` (VPS Docker + PostgreSQL)  
> **Data de Elaboração:** 03 de Novembro de 2026  
> **Responsável:** Rodrigo Cardoso / Antigravity AI  

---

## 1. 📌 Resumo Executivo

Este projeto consiste em uma plataforma de organização e catalogação visual de **57 fotos em alta resolução** da Casa de Peruíbe, com categorização por ambientes (*Piscina*, *Corredor das Plantas*, *Área Gourmet*, etc.), reordenação dinâmica de cartões (Kanban) e proteção contra edição indevida.

Toda a camada pesada de mídia já foi processada e enviada para a nuvem. O objetivo atual é acoplar a persistência de dados ao ecossistema oficial **`dixty_office`**, utilizando o **PostgreSQL** da VPS para armazenar as categorias e posições das fotos em tempo real.

---

## 2. ☁️ Infraestrutura de Mídia no Azure Blob Storage

Todas as 57 fotos e suas respectivas miniaturas já estão armazenadas na conta Azure da Dixty.

* **Storage Account:** `dixty`
* **Container:** `others`
* **Prefixo base:** `casa-peruibe/`
* **Vigência da Chave SAS:** Válida até **31/12/2035** (`2035-12-31T23:59:59Z`)
* **Permissões do SAS:** `racwdl` (Read, Add, Create, Write, Delete, List)
* **Estrutura dos Blobs:**
  * `others/casa-peruibe/full/`: 57 fotos originais (~500 MB no total, 4284x5712 px).
  * `others/casa-peruibe/thumbnails/`: 57 miniaturas otimizadas (compressão Web/Lanczos, orientação EXIF corrigida para iPhone, ~15 a 50 KB cada).

#### URL Base e Assinatura SAS:
```text
https://dixty.blob.core.windows.net/others/casa-peruibe/thumbnails/{FILENAME}?se=2035-12-31T23%3A59%3A59Z&sp=racwdl&spr=https&sv=2026-04-06&sr=c&sig=jEZ%2BWnVX1pyP3%2Bp8K5DqSxUze/m0%2Bga7SgYdQdFckf4%3D
```

---

## 3. 🔐 Segurança & Regras de Acesso

* **Modo Padrão de Leitura:** Qualquer usuário que acessar a URL pública entra em modo **🔒 Bloqueado**. Ele pode navegar, dar zoom nas fotos em alta definição (Lightbox), filtrar por nome e copiar relatórios, mas **não pode mover fotos nem alterar a ordem dos cards**.
* **Senha de Edição:** `Pandora01@`
* **Ao Destravar (`🔓 Modo Edição`):**
  * Habilita drag & drop de fotos entre ambientes.
  * Habilita reordenação de cards (via arrasto `⠿` ou setas `◀ ▶`).
  * Habilita criação de novos locais e exclusão.

---

## 4. 🗄️ Modelagem de Dados no PostgreSQL (`dixty_office`)

Um arquivo pronto para execução foi gerado: [`schema_seed.sql`](file:///Users/rodrigocardoso/Desktop/Fotos%20Casa%20Peruibe%20-%20Adicionais/schema_seed.sql).

### DDL das Tabelas:

```sql
CREATE SCHEMA IF NOT EXISTS peruibe;

-- 1. Tabela de Categorias / Ambientes
CREATE TABLE IF NOT EXISTS peruibe.categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    order_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Tabela de Fotos
CREATE TABLE IF NOT EXISTS peruibe.photos (
    id VARCHAR(100) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    thumb_url TEXT NOT NULL,
    full_url TEXT NOT NULL,
    category_id INTEGER REFERENCES peruibe.categories(id) ON DELETE SET NULL,
    order_index INTEGER NOT NULL DEFAULT 0,
    width INTEGER,
    height INTEGER,
    size_bytes BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Índices para busca ultrarrápida
CREATE INDEX IF NOT EXISTS idx_photos_category ON peruibe.photos(category_id);
CREATE INDEX IF NOT EXISTS idx_categories_order ON peruibe.categories(order_index);
CREATE INDEX IF NOT EXISTS idx_photos_order ON peruibe.photos(order_index);
```

> O script [`schema_seed.sql`](file:///Users/rodrigocardoso/Desktop/Fotos%20Casa%20Peruibe%20-%20Adicionais/schema_seed.sql) já contém os inserts de todas as **57 fotos com seus metadados completos e links do Azure**.

---

## 5. 🚀 Arquitetura Backend Sugerida para a VPS

Para integrar com o `docker-compose.yml` do `dixty_office`, sugerimos um micro-serviço Node.js/Express ou Python/FastAPI simples com 4 endpoints:

### Endpoints REST:

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/peruibe/state` | Retorna categorias e fotos na ordem definida (Público). |
| `POST` | `/api/peruibe/auth` | Valida a senha (`Pandora01@`) e retorna token JWT/Session. |
| `PUT` | `/api/peruibe/photo/move` | Altera o `category_id` e `order_index` da foto movida. |
| `PUT` | `/api/peruibe/categories/reorder` | Atualiza a sequência `order_index` dos ambientes. |
| `POST` | `/api/peruibe/category` | Cria um novo ambiente (ex: "Jardim de Inverno"). |
| `DELETE` | `/api/peruibe/category/:id` | Remove o ambiente (fotos voltam a `category_id = NULL`). |

### Exemplo de Controller Express (Node.js):
```javascript
// GET /api/peruibe/state
app.get('/api/peruibe/state', async (req, res) => {
  const categories = await db.query('SELECT * FROM peruibe.categories ORDER BY order_index ASC');
  const photos = await db.query('SELECT * FROM peruibe.photos ORDER BY order_index ASC');
  res.json({ categories: categories.rows, photos: photos.rows });
});

// PUT /api/peruibe/photo/move
app.put('/api/peruibe/photo/move', requireAuth, async (req, res) => {
  const { photoId, categoryId, orderIndex } = req.body;
  await db.query(
    'UPDATE peruibe.photos SET category_id = $1, order_index = $2, updated_at = NOW() WHERE id = $3',
    [categoryId, orderIndex || 0, photoId]
  );
  res.json({ success: true });
});
```

---

## 6. 🐳 Integração no Docker Compose do `dixty_office`

No `docker-compose.yml` da sua VPS:

```yaml
  peruibe-api:
    build:
      context: ./apps/pessoal/casa_peruibe
      dockerfile: Dockerfile
    container_name: peruibe_app
    restart: unless-stopped
    environment:
      - PORT=3005
      - DATABASE_URL=postgresql://office_admin:${DB_PASSWORD}@postgres:5432/office_auth_db
      - ADMIN_PASSWORD=Pandora01@
    networks:
      - office-net
    depends_on:
      - postgres
```

### Configuração no Nginx (`nginx.conf` da VPS):
```nginx
location /casa-peruibe/ {
    proxy_pass http://peruibe-api:3005/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

---

## 7. 📂 Inventário dos Arquivos no Diretório Local

| Arquivo / Pasta | Finalidade |
|---|---|
| [`index.html`](file:///Users/rodrigocardoso/Desktop/Fotos%20Casa%20Peruibe%20-%20Adicionais/index.html) | Aplicação Frontend completa com visual moderno, Lightbox, Drag & Drop e trava de senha. |
| [`schema_seed.sql`](file:///Users/rodrigocardoso/Desktop/Fotos%20Casa%20Peruibe%20-%20Adicionais/schema_seed.sql) | DDL completo + carga inicial (Seed) das 57 fotos com links Azure no Postgres. |
| [`fotos_manifest.json`](file:///Users/rodrigocardoso/Desktop/Fotos%20Casa%20Peruibe%20-%20Adicionais/fotos_manifest.json) | Manifesto JSON com os metadados brutos das 57 fotos. |
| [`upload_azure.py`](file:///Users/rodrigocardoso/Desktop/Fotos%20Casa%20Peruibe%20-%20Adicionais/upload_azure.py) | Script de automação que processou EXIF, gerou thumbnails e fez upload em paralelo no Azure. |
| [`publicar.py`](file:///Users/rodrigocardoso/Desktop/Fotos%20Casa%20Peruibe%20-%20Adicionais/publicar.py) | Script de sincronização com o GitHub Pages (`DigoDixty/casa-peruibe-fotos`). |
| [`Fotos/`](file:///Users/rodrigocardoso/Desktop/Fotos%20Casa%20Peruibe%20-%20Adicionais/Fotos) | Pasta local com as 57 fotos originais em alta resolução. |
| [`thumbnails/`](file:///Users/rodrigocardoso/Desktop/Fotos%20Casa%20Peruibe%20-%20Adicionais/thumbnails) | Pasta local com as 57 miniaturas otimizadas. |

---

## 8. 🎯 Checklist para o Próximo Passo no `dixty_office`

- [ ] Copiar os arquivos [`index.html`](file:///Users/rodrigocardoso/Desktop/Fotos%20Casa%20Peruibe%20-%20Adicionais/index.html) e [`schema_seed.sql`](file:///Users/rodrigocardoso/Desktop/Fotos%20Casa%20Peruibe%20-%20Adicionais/schema_seed.sql) para dentro de `dixty_office/apps/pessoal/casa_peruibe`.
- [ ] Rodar o [`schema_seed.sql`](file:///Users/rodrigocardoso/Desktop/Fotos%20Casa%20Peruibe%20-%20Adicionais/schema_seed.sql) no PostgreSQL da VPS (`psql -U office_admin -d office_auth_db -f schema_seed.sql`).
- [ ] Criar a rota de API simples para responder ao frontend.
- [ ] Apontar o subdomínio ou caminho Nginx desejado.
