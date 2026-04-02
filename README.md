# JoorDames

Automatisation des réservations de bureau sur [doorjames.app](https://doorjames.app).

JoorDames réserve automatiquement un bureau **41 jours à l'avance**, effectue le check-in chaque matin, et annule les réservations les jours où vous n'êtes pas au bureau. Le tout piloté par votre agenda Google Calendar, avec des notifications Discord à chaque action.

---

## Comment ça marche

### Le mécanisme de re-réservation

JoorDames ne recherche pas de bureaux disponibles — il **réutilise un bureau de votre historique**.

À chaque exécution du script de réservation :

1. L'application ouvre votre liste d'**anciennes réservations** sur doorjames.app
2. Elle y cherche la première réservation avec un statut éligible : *checked out*, *automatically checked out*, ou *cancelled*
3. Elle réserve **ce même bureau** pour la date cible (41 jours à l'avance)

> ⚠️ **Important — choisissez bien votre bureau de référence**
>
> Avant de lancer JoorDames, assurez-vous que la **première** réservation éligible dans votre historique correspond au bureau que vous souhaitez réserver automatiquement. Si ce n'est pas le cas, faites une réservation manuelle sur le bon bureau, laissez-la se terminer (ou annulez-la) — elle deviendra alors la référence utilisée par JoorDames.

### La période de démarrage

JoorDames réserve **41 jours à l'avance**. Cela signifie que lors de la mise en place, les prochaines semaines ne seront pas automatiquement couvertes. Vous devrez **continuer à réserver manuellement** jusqu'à ce que les réservations automatiques commencent à prendre le relai, soit environ 6 semaines après l'installation.

### Le fichier `bookings.csv`

JoorDames maintient un fichier `bookings.csv` qui trace le statut de chaque jour à venir. C'est ce fichier qui permet à l'application de savoir quoi faire chaque matin.

| Statut | Signification |
|---|---|
| `booked` | Bureau réservé, check-in à effectuer |
| `checked_in` | Check-in effectué |
| `cancelled` | Réservation annulée |
| `out of office - remote` | Jour de télétravail (via Google Calendar) |
| `out of office - holidays` | Congés (via Google Calendar) |
| `out of office - public holiday` | Jour férié |

Chaque matin, le script de check-in consulte ce fichier pour décider quoi faire :
- Statut `booked` → check-in sur doorjames.app
- Statut `out of office - *` → annulation de la réservation existante (si elle existe)
- Aucun statut → check-in tenté (voir ci-dessous)

> **Sans Google Calendar**, JoorDames ne sait pas si vous êtes au bureau ou non. Il tentera un check-in tous les jours ouvrés, même les jours de télétravail ou de congé. L'intégration Google Calendar est donc fortement recommandée pour éviter des check-ins indésirables.

---

## Fonctionnalités

### Sans intégrations
- Réservation automatique du bureau J+41
- Check-in automatique chaque matin en semaine
- Le script tente toujours le check-in — **sans Google Calendar, vous devrez annuler manuellement les jours où vous n'êtes pas au bureau**

### Avec Google Calendar *(optionnel — fortement recommandé)*

L'intégration Google Calendar permet d'alimenter et d'affiner automatiquement le calendrier `bookings.csv`. C'est ce qui rend JoorDames vraiment autonome : en renseignant vos jours de télétravail et de congé dans votre agenda, vous n'avez plus rien à faire manuellement.

C'est aussi une question de **courtoisie envers vos collègues** : libérer automatiquement les créneaux sur lesquels vous n'avez pas besoin d'un bureau permet à ceux qui en ont besoin d'en trouver un plus facilement.

JoorDames synchronise votre agenda chaque matin et met à jour `bookings.csv` en conséquence. Pour cela, il s'appuie sur les **noms de vos événements** Google Calendar :

- **Jours de télétravail** : événements dont le titre contient un ou plusieurs mots-clés que vous définissez (ex : `Remote`, `Télétravail`). Ces jours, aucune réservation n'est faite, et le check-in est ignoré.
- **Congés** : événements dont le titre contient d'autres mots-clés (ex : `Congé`, `Vacances`). Ces jours, toute réservation existante est annulée.
- **Jours fériés** : détectés automatiquement, sans configuration nécessaire.

Ces mots-clés sont configurés dans votre fichier `.env` (voir [Configuration Google Calendar](docs/setup-google-calendar.md)) :

```
REMOTE_WORKING_PATTERNS=Remote,Télétravail
OUT_OF_OFFICE_PATTERNS=Congé,Vacances
```

### Avec Discord *(optionnel)*
- Notification à chaque action (réservation, check-in, annulation, erreur)
- Notifications silencieuses les week-ends, jours fériés et jours de congé
- Rappel le week-end si les événements de télétravail de la semaine suivante ne sont pas renseignés dans l'agenda *(nécessite Google Calendar + Discord)*
- Commande `skip` depuis un canal Discord pour ignorer l'action du jour (check-in ou annulation) sans accès au terminal

Voir [Configuration Discord](docs/setup-discord.md) pour la mise en place.

---

## Planning des tâches automatiques

Les horaires ci-dessous sont ceux par défaut. Ils sont entièrement personnalisables dans votre crontab lors de l'installation.

| Heure | Fréquence | Action |
|---|---|---|
| 6h00 | Tous les jours | Synchronisation Google Calendar |
| 8h00 | Tous les jours | Réservation du bureau J+41 |
| 8h45 | Lundi–Vendredi | Check-in (ou annulation si absent) |
| 14h00 | Samedi | Rappel télétravail semaine suivante *(Discord + Google Calendar)* |
| 20h00 | Dimanche | Rappel télétravail semaine suivante *(Discord + Google Calendar)* |

> Le script de synchronisation Google Calendar doit s'exécuter **avant** la réservation, elle-même **avant** le check-in, pour que les statuts soient à jour au moment où chaque action se déclenche.

---

## Installation

Deux options d'installation sont disponibles :

- **[Installation standard (recommandée)](docs/installation-standard.md)** — Python directement sur votre machine, sans Docker
- **[Installation Docker](docs/installation-docker.md)** — Pour ceux qui préfèrent un environnement isolé

---

## Commandes disponibles

```bash
python src/main.py auth      # Authentification manuelle (première fois ou session expirée)
python src/main.py book      # Réserver le bureau J+41
python src/main.py checkin   # Check-in du jour (ou annulation si absent)
python src/main.py cancel    # Annuler la réservation du jour
python src/main.py sync      # Synchroniser Google Calendar
python src/main.py reminder  # Envoyer le rappel télétravail
```

---

## Commande Discord

Envoyez `skip` dans le canal de commande Discord configuré avant l'heure du check-in pour ignorer l'action automatique du jour (check-in ou annulation selon votre statut).
