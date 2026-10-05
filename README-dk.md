# Burst Shot Cleaner

Et Python-baseret GUI-værktøj designet til at finde og reducere burst-shots i billedmapper. Det identificerer sekvenser af billeder taget inden for en kort tidsramme (1-2 sekunder) og beholder kun det første, midterste og sidste billede, flytter de andre til et sikkert oprydningsarkiv.

## Funktioner
- **Intelligent detektion**: Scanner efter billeder med næsten identiske tidsstempler eller sekventielle "BURST"-navngivningsmønstre.
- **Sikker oprydning**: I stedet for at slette filer, flytter dem til en tidsbestemt `cleanup_archive`-mappe.
- **Tør-kørselstilstand**: Se præcis hvad der sker, før du forpligter dig til ændringer.
- **Visuel feedback**: Real-time fremskridtssporing og pladsbesparende statistik.
- **Modern grænseflade**: Bygget med CustomTkinter for en elegant, mørk-tematisk oplevelse.

## Installation og start
Den nemmeste måde at køre Burst Shot Cleaner på er gennem det medfølgende start-script:

```bash
chmod +x launch.sh
./launch.sh
```

Dette script vil automatisk oprette et virtuelt miljø, installere de nødvendige afhængigheder (`customtkinter`, `pillow`, `pandas`) og starte applikationen.

## Brug
1. Vælg de mappe der skal scannes (standard: `$HOME/Pictures` og `/run/media/$USER/DATA/Billeder`).
2. Juster burst-tærsklen hvis nødvendigt (standard 2 sekunder).
3. Klik på **Scan** for at finde burst-sekvenser.
4. Gennemgå de fundne grupper.
5. Klik på **Kør Oprydning** (eller sørg for at 'Tør Kørsel' er markeret først for at forhåndsvise).