

Parfait. Voici **les deux livrables**, prêts à l’emploi, **sans ambiguïté**.

---

# 1️⃣ `README.fr.md` — Version française officielle

👉 À créer **à la racine du projet**, à côté de `README.md`.

````markdown
# iBCB RocketMail

iBCB RocketMail est une plateforme backend d’automatisation d’e-mails développée avec FastAPI.  
Elle fournit une base propre et évolutive pour la gestion de contacts, l’envoi d’e-mails transactionnels ou en masse, ainsi que la configuration sécurisée des paramètres liés aux e-mails.

Ce projet est publié comme un **projet portfolio backend professionnel**, démontrant une architecture réaliste, une API robuste et une gestion sérieuse des configurations et de la sécurité.

---

## 🚀 Fonctionnalités

- API REST construite avec **FastAPI**
- Envoi d’e-mails simples et en masse
- Gestion modulaire des paramètres :
  - Configuration SMTP
  - Domaines
  - Clés API
  - Facturation (structure prête)
- Logique de campagnes et de contacts
- Gestion sécurisée des variables d’environnement
- Support Docker et Docker Compose
- Documentation interactive de l’API (Swagger / OpenAPI)

---

## 🧱 Stack technique

- **Python 3**
- **FastAPI**
- **Pydantic**
- **PostgreSQL / SQLite (développement)**
- **SMTP (compatible Gmail)**
- **Docker & Docker Compose**

---

## 📁 Structure du projet

```text
email_contacts_backend/
├── app/
│   ├── api/
│   ├── routers/
│   ├── services/
│   ├── utils/
│   ├── models.py
│   ├── schemas.py
│   ├── db.py
│   └── main.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── run_simple_worker.py
````

Le projet suit une **séparation claire des responsabilités** afin de rester maintenable et scalable.

---

## ⚙️ Configuration de l’environnement

Toutes les données sensibles sont gérées via des variables d’environnement.

Créer un fichier `.env` à partir de l’exemple :

```bash
cp .env.example .env
```

Puis configurer :

* La base de données
* Les identifiants SMTP
* Les paramètres de sécurité (JWT, secrets)

⚠️ **Ne jamais versionner le fichier `.env` réel.**

---

## ▶️ Lancer le projet

### Option 1 — En local (Python)

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Option 2 — Avec Docker

```bash
docker-compose up --build
```

---

## 📖 Documentation API

Une fois l’application lancée :

* Swagger UI :
  👉 `http://localhost:8000/docs`

* OpenAPI / ReDoc :
  👉 `http://localhost:8000/redoc`

---

## 🔐 Sécurité

* Aucun secret en dur dans le code
* Identifiants SMTP externalisés
* Bonnes pratiques de sécurité backend
* `.gitignore` configuré pour éviter toute fuite

---

## 🎯 Objectif du projet

Ce projet est volontairement publié comme un **projet portfolio backend**.

Il démontre :

* Une architecture API professionnelle
* Une logique d’automatisation d’e-mails
* Une utilisation correcte de Git
* Un workflow Dockerisé

Il pourra ensuite évoluer vers :

* Un produit SaaS
* Un service interne d’envoi d’e-mails
* Une base backend pour des systèmes de notification ou marketing

---

## 📌 Auteur

**iBCB**
Projet : **iBCB RocketMail**

---

## 📜 Licence

MIT License

````

---

# 2️⃣ Fichier `LICENSE` — Licence MIT

👉 À créer **à la racine du projet**, nommé exactement `LICENSE` (sans extension).

```text
MIT License

Copyright (c) 2025 iBCB

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
````

---

# 3️⃣ Commits recommandés (dans cet ordre)

```bash
git add README.fr.md LICENSE
git commit -m "docs: add French README and MIT license"
```

---

