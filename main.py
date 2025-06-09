import os
import asyncio
import signal
import sys
import schedule
import time
import threading
import argparse
from datetime import datetime
from src.streamer_watcher import monitor_streamers
from src.bestof_generator import generate_weekly_bestof


# Configuration
GAME_ID = "32982"  # ID de GTA V
SEARCH_TERMS = ["[MindCityRP]", "[MindCity]", "[MindCity RP]", "[MindCity-RP]"]
# SEARCH_TERMS = [
#     "[RerollRP]",
#     "[Reroll]",
#     "[Reroll RP]",
#     "[Reroll-RP]",
#     "[Reroll-RP]",
#     "[Reroll RP]",
#     "[RerollRP]",
#     "[Reroll]",
#     "Reroll",
#     "RerollRP",
# ]
CHECK_INTERVAL_MINUTES = 15
BESTOF_DAY = "sunday"  # Jour de génération du best-of

# Variable pour contrôler l'arrêt du programme
running = True


# Fonction pour exécuter le générateur de best-of
def run_bestof_generator():
    print(
        f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Démarrage de la génération du best-of hebdomadaire..."
    )
    asyncio.run(generate_weekly_bestof()) # type: ignore
    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Génération du best-of terminée."
    )


# Fonction pour exécuter le planificateur dans un thread séparé
def run_scheduler():
    while running:
        schedule.run_pending()
        time.sleep(60)  # Vérifier toutes les minutes


# Gestionnaire de signal pour arrêter proprement le programme
def signal_handler(sig, frame):
    global running
    print("\nArrêt du programme en cours...")
    running = False
    sys.exit(0)


async def main():
    global running

    # Analyser les arguments de ligne de commande
    parser = argparse.ArgumentParser(
        description="BestOfMaker - Génère des best-of de clips Twitch"
    )
    parser.add_argument(
        "--bestof",
        action="store_true",
        help="Générer immédiatement un best-of puis quitter",
    )
    parser.add_argument(
        "--clips",
        type=int,
        default=20,
        help="Nombre de clips à inclure dans le best-of (défaut: 20)",
    )
    parser.add_argument(
        "--monitor",
        action="store_true",
        help="Lancer uniquement la surveillance des streamers",
    )
    args = parser.parse_args()

    # Mode génération immédiate de best-of
    if args.bestof:
        print(f"=== BestOfMaker - Génération de best-of à la demande ===")
        print(f"Nombre de clips demandés: {args.clips}")
        await generate_weekly_bestof(total_bestof_clips=args.clips)
        return

    # Mode surveillance uniquement
    if args.monitor:
        print(f"=== BestOfMaker - Mode surveillance uniquement ===")
        print(f"Surveillance des streamers pour les termes: {', '.join(SEARCH_TERMS)}")
        await monitor_streamers(
            GAME_ID, SEARCH_TERMS, interval_minutes=CHECK_INTERVAL_MINUTES
        )
        return

    # Mode normal (surveillance + génération planifiée)
    print(f"=== BestOfMaker - Mode complet ===")
    print(f"Service de surveillance des streamers pour {', '.join(SEARCH_TERMS)}")
    print(f"Génération du best-of hebdomadaire prévue chaque {BESTOF_DAY}")
    print(f"Utilisez Ctrl+C pour arrêter le programme, ou:")
    print(f"  --bestof pour générer immédiatement un best-of")
    print(f"  --monitor pour lancer uniquement la surveillance")

    # Planifier la génération du best-of hebdomadaire
    schedule.every().sunday.at("00:00").do(run_bestof_generator)

    # Démarrer le planificateur dans un thread séparé
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    # Configurer le gestionnaire de signal
    signal.signal(signal.SIGINT, signal_handler)

    # Lancer la surveillance des streamers (s'exécute indéfiniment jusqu'à interruption)
    await monitor_streamers(
        GAME_ID,
        SEARCH_TERMS,
        interval_minutes=CHECK_INTERVAL_MINUTES,
    )


if __name__ == "__main__":
    asyncio.run(main())
