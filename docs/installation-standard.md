# Installation standard (sans Docker)

Ce guide explique comment installer et configurer JoorDames directement sur votre machine, sans Docker.

---

## 1. Prérequis

- Python 3.10 ou supérieur
- `pip` (inclus avec Python)
- `git`
- Une machine Linux ou macOS avec support cron (`crontab`)

> Windows n'est pas supporté. Si vous êtes sur Windows, utilisez WSL2 ou le guide d'installation Docker.

Vérifiez votre version de Python :

```bash
python3 --version
```

---

## 2. Cloner le dépôt

```bash
git clone https://github.com/BNWCZ/JoorDames.git
cd JoorDames
```

---

## 3. Installer les dépendances

Installez les bibliothèques Python :

```bash
pip install -r requirements.txt
```

Installez le navigateur Chromium utilisé par Playwright :

```bash
playwright install chromium
```

---

## 4. Configurer l'environnement

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

## 5. Première authentification

La première connexion nécessite une approbation manuelle de la double authentification (2FA) sur votre téléphone.

1. Lancez la commande d'authentification :

```bash
python src/main.py auth
```

2. Une fenêtre de navigateur s'ouvre. Renseignez vos identifiants sur doorjames.app.

3. Une invitation 2FA s'affiche sur votre téléphone (Microsoft Authenticator). Approuvez-la.

4. Une fois connecté dans le navigateur, revenez dans le terminal et appuyez sur **Entrée**.

5. La session est sauvegardée dans `session/state.json`. Les exécutions suivantes utiliseront ce fichier sans redemander de 2FA.

> Si la session expire, relancez `python src/main.py auth` pour vous réauthentifier.

---

## 6. Tester manuellement chaque mode

Une fois l'authentification faite, testez chaque mode pour vérifier que tout fonctionne.

**Synchronisation avec Google Calendar :**

```bash
python src/main.py sync
```

Lit votre agenda sur les 90 prochains jours et met à jour `bookings.csv` avec les jours de télétravail, de congé ou de jours fériés détectés.

**Réservation de bureau :**

```bash
python src/main.py book
```

Réserve un bureau pour le jour situé 41 jours dans le futur (créneau 09:00–17:00), sauf si ce jour est déjà réservé ou marqué hors du bureau dans `bookings.csv`.

**Check-in :**

```bash
python src/main.py checkin
```

Effectue le check-in pour la réservation d'aujourd'hui. Si aujourd'hui est marqué hors du bureau dans `bookings.csv`, annule la réservation du jour à la place. À lancer après 8h30.

**Annulation :**

```bash
python src/main.py cancel
```

Annule la réservation d'aujourd'hui si elle existe.

**Rappel :**

```bash
python src/main.py reminder
```

Envoie une notification Discord si des événements de télétravail ne sont pas renseignés pour la semaine suivante.

---

## 7. Configurer les tâches cron

Ouvrez l'éditeur de crontab :

```bash
crontab -e
```

Ajoutez les lignes suivantes en remplaçant `/home/USER/JoorDames` par le chemin absolu de votre installation :

```
0 6 * * *     cd /home/USER/JoorDames && python src/main.py sync >> cron.log 2>&1
0 8 * * *     cd /home/USER/JoorDames && python src/main.py book >> cron.log 2>&1
45 8 * * 1-5  cd /home/USER/JoorDames && python src/main.py checkin >> cron.log 2>&1
0 14 * * 6    cd /home/USER/JoorDames && python src/main.py reminder >> cron.log 2>&1
0 20 * * 0    cd /home/USER/JoorDames && python src/main.py reminder >> cron.log 2>&1
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

> Les chemins dans les tâches cron doivent être absolus. L'utilisation de `~` peut ne pas fonctionner selon la configuration cron de votre système.

Sauvegardez et quittez l'éditeur. Vérifiez que les tâches sont bien enregistrées :

```bash
crontab -l
```

---

## 8. Vérification finale

Les logs de toutes les exécutions cron sont écrits dans `cron.log` à la racine du projet.

Pour suivre les logs en temps réel :

```bash
tail -f /home/USER/JoorDames/cron.log
```

Pour consulter les dernières lignes :

```bash
tail -50 /home/USER/JoorDames/cron.log
```

> Si une tâche cron ne produit aucun log, vérifiez que le service cron est bien actif sur votre machine (`systemctl status cron` ou `systemctl status crond`).
