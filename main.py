"""Wind Fireworks Simulation entry point."""

import pygame

from app import main


if __name__ == "__main__":
    try:
        main()
    except pygame.error:
        pygame.quit()
        print(
            "Program başlatılamadı: grafik penceresi oluşturulamadı.\n"
            "Ekran sürücüsünü kontrol edip programı yeniden çalıştırın."
        )
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        pygame.quit()
        print("Program kullanıcı tarafından durduruldu.")
        raise SystemExit(0) from None
