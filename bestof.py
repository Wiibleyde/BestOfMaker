#!/usr/bin/env python3
"""
Script pour générer rapidement un best-of de clips Twitch.
Utilitaire en ligne de commande dédié à la génération de best-of.
"""

import asyncio
import argparse
from src.bestof_generator import generate_weekly_bestof

async def main():
    parser = argparse.ArgumentParser(description='Générateur de best-of de clips Twitch')
    parser.add_argument('--clips', type=int, default=20, 
                        help='Nombre de clips à inclure dans le best-of (défaut: 20)')
    parser.add_argument('--streamer-clips', type=int, default=30, 
                        help='Nombre maximum de clips à récupérer par streamer (défaut: 30)')
    
    args = parser.parse_args()
    
    print("=== Générateur de Best-Of de Clips Twitch ===")
    print(f"Génération d'un best-of avec les {args.clips} meilleurs clips...")
    
    await generate_weekly_bestof(
        max_clips_per_streamer=args.streamer_clips,
        total_bestof_clips=args.clips
    )
    
    print("Génération terminée.")

if __name__ == "__main__":
    asyncio.run(main())
