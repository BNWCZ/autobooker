# Installation avec Docker

Ce guide explique comment installer et configurer JoorDames en utilisant Docker et Docker Compose.

---

## 1. Prérequis

- Docker (version 20.10 ou supérieure)
- Docker Compose (version 2.x ou supérieure — commande `docker compose`)
- `git`

Vérifiez que Docker est disponible :

```bash
docker --version
docker compose version
```

---

## 2. Cloner le dépôt

```bash
git clone https://github.com/BNWCZ/JoorDames.git
cd JoorDames
```

---

## 3. Configurer l'environnement

Copiez le fichier d'exemple :

```bash
cp .env.example .env
```

Ouvrez `.env` et renseignez au minimum les variables suivantes :

```env
APP_URL=https://doorjames.app
SESSION_STATE_PATH=session/state.json
BOOKINGS_PATH=bookings.csv
```

**`APP_URL`** — L'URL de l'application de réservation. Ne pas modifier sauf si l'URL change.

**`SESSION_STATE_PATH`** — Chemin vers le fichier de session Playwright. Ce fichier est créé automatiquement lors de la première authentification.

**`BOOKINGS_PATH`** — Chemin vers le fichier CSV qui enregistre l'état des réservations.

> Pour activer l'intégration Google Calendar, consultez [setup-google-calendar.md](setup-google-calendar.md).
> Pour activer les notifications et la commande skip Discord, consultez [setup-discord.md](setup-discord.md).

---

## 4. Construire l'image

```bash
docker compose build
```

Cette commande télécharge l'image de base (`mcr.microsoft.com/playwright/python:v1.49.1-jammy`) et installe les dépendances du projet. L'opération peut prendre quelques minutes lors du premier build.

---

## 5. Première authentification

La première connexion nécessite une approbation manuelle de la double authentification (2FA) sur votre téléphone. Cette étape **ne peut pas être effectuée directement dans Docker** car elle requiert un navigateur graphique visible.

La méthode la plus simple est de lancer l'authentification en dehors de Docker, directement sur votre machine hôte :

1. Assurez-vous d'avoir Python 3.10+ et les dépendances installées localement (voir le [guide d'installation standard](installation-standard.md) sections 3 et 4).

2. Lancez l'authentification en dehors de Docker :

```bash
python src/main.py auth
```

3. Une fenêtre de navigateur s'ouvre. Renseignez vos identifiants sur doorjames.app.

4. Une invitation 2FA s'affiche sur votre téléphone (Microsoft Authenticator). Approuvez-la.

5. Une fois connecté dans le navigateur, revenez dans le terminal et appuyez sur **Entrée**.

6. La session est sauvegardée dans `session/state.json`. Toutes les exécutions Docker suivantes utiliseront ce fichier.

> Le fichier `session/state.json` est monté dans le conteneur via Docker Compose. Une fois créé sur votre machine hôte, il est automatiquement accessible au conteneur.

> Si la session expire, relancez `python src/main.py auth` hors de Docker pour vous réauthentifier.

---

## 6. Tester manuellement chaque mode

**Synchronisation avec Google Calendar :**

```bash
docker compose run --rm joordames python src/main.py sync
```

Lit votre agenda sur les 90 prochains jours et met à jour `bookings.csv` avec les jours de télétravail, de congé ou de jours fériés détectés.

**Réservation de bureau :**

```bash
docker compose run --rm joordames python src/main.py book
```

Réserve un bureau pour le jour situé 41 jours dans le futur (créneau 09:00–17:00), sauf si ce jour est déjà réservé ou marqué hors du bureau dans `bookings.csv`.

**Check-in :**

```bash
docker compose run --rm joordames python src/main.py checkin
```

Effectue le check-in pour la réservation d'aujourd'hui. Si aujourd'hui est marqué hors du bureau dans `bookings.csv`, annule la réservation du jour à la place.

**Annulation :**

```bash
docker compose run --rm joordames python src/main.py cancel
```

Annule la réservation d'aujourd'hui si elle existe.

**Rappel :**

```bash
docker compose run --rm joordames python src/main.py reminder
```

Envoie une notification Discord si des événements de télétravail ne sont pas renseignés pour la semaine suivante.

---

## 7. Configurer les tâches cron

Ouvrez l'éditeur de crontab sur la machine hôte :

```bash
crontab -e
```

Ajoutez les lignes suivantes en remplaçant `/home/USER/JoorDames` par le chemin absolu de votre installation :

```
0 6 * * *     cd /home/USER/JoorDames && docker compose run --rm joordames python src/main.py sync >> cron.log 2>&1
0 8 * * *     cd /home/USER/JoorDames && docker compose run --rm joordames python src/main.py book >> cron.log 2>&1
45 8 * * 1-5  cd /home/USER/JoorDames && docker compose run --rm joordames python src/main.py checkin >> cron.log 2>&1
0 14 * * 6    cd /home/USER/JoorDames && docker compose run --rm joordames python src/main.py reminder >> cron.log 2>&1
0 20 * * 0    cd /home/USER/JoorDames && docker compose run --rm joordames python src/main.py reminder >> cron.log 2>&1
```

**Explication des tâches :**

| Heure | Mode | Description |
|---|---|---|
| 6h00 tous les jours | `sync` | Synchronise Google Calendar et met à jour `bookings.csv` |
| 8h00 tous les jours | `book` | Réserve le bureau pour J+41 |
| 8h45 du lundi au vendredi | `checkin` | Check-in ou annulation selon le statut du jour |
| 14h00 le samedi | `reminder` | Rappel si la semaine suivante n'est pas renseignée |
| 20h00 le dimanche | `reminder` | Rappel de dernière minute pour le lundi |

> L'ordre des tâches est important : `sync` doit toujours s'exécuter avant `book`, et `book` avant `checkin`.

> Chaque exécution de `docker compose run --rm` démarre un conteneur temporaire qui s'arrête automatiquement une fois la commande terminée.

Sauvegardez et quittez l'éditeur. Vérifiez que les tâches sont bien enregistrées :

```bash
crontab -l
```

---

## 8. Vérification

Les logs de toutes les exécutions cron sont écrits dans `cron.log` à la racine du projet.

Pour suivre les logs en temps réel :

```bash
tail -f /home/USER/JoorDames/cron.log
```

Pour consulter les dernières lignes :

```bash
tail -50 /home/USER/JoorDames/cron.log
```

> Si une tâche cron ne produit aucun log, vérifiez que le service cron est bien actif sur votre machine (`systemctl status cron` ou `systemctl status crond`) et que la commande `docker compose` est accessible dans le PATH utilisé par cron.
