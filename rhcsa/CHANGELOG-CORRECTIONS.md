# Correcties — 2 oktober 2026

Deze revisie past theorie, opdrachten, gegenereerde labpagina's en installatiecode aan voor Rocky/RHEL 10. Het oorspronkelijke archief is niet gewijzigd. De oorspronkelijke licentie blijft gelden.

## Belangrijkste wijzigingen

- Alle twaalf weken: benodigde pakketten, uitvoercontext, herstartcontroles en verwachte resultaten verduidelijkt. De bron in `tools/build_labs.py` en alle labpagina's komen overeen.
- Gebruikers en rechten: groepsschrijfrechten, umask, beperkte sudo-rechten en afzonderlijke oefengebruikers gecorrigeerd.
- Software: lokale RPM-downloads en repository-opbouw gecorrigeerd; Flatpak en RHEL-abonnementen krijgen passende voorwaarden.
- Taken en services: geplande at-taken blijven lang genoeg beschikbaar; procesbeheer gebruikt bijgehouden procesnummers; servicefouten zijn reproduceerbaar.
- Boot en herstel: herstel via `rw init=/bin/bash enforcing=0` gebruikt `/` in de geïnstalleerde omgeving. Dit voorkomt de verwarring tussen `/` en `/sysroot` bij een geblokkeerde rd.break-console. SELinux-herlabeling en hervatten van de boot zijn opgenomen. GRUB-timeout en kernelargumenten zijn gescheiden.
- Logging: journald gebruikt een configuratiedrop-in, zodat een ontbrekende `/etc/systemd/journald.conf` geen probleem is. Flush, herkenbare berichten en controles over herstarts zijn opgenomen.
- Netwerk: host-only-profiel wordt expliciet gekozen; NAT behoudt de standaardroute. Firewalltests gebruiken de juiste zone en een nieuwe tijdelijke poort.
- Opslag: diskselectie en partitiebenaming werken met SATA, NVMe en MMC. Latere weken behouden eerdere partities. UUID/fstab, groei, offline verkleinen, NFS en autofs zijn verduidelijkt.
- SELinux en toegang: Apache-toegangsrechten worden eerst juist gezet; contexten en poorten krijgen passende controles. SSH-configuratie wordt gevalideerd voor herstart.
- Shellscripts: argumenten, spaties in namen, getalgrenzen en foutstatussen gecorrigeerd.
- Theorie: onbewezen examengewichten en garanties verwijderd of afgezwakt; platform-, virtualisatie- en cursusclaims bijgewerkt.
- Lokale builders: architectuurcontrole, eigendomsmarkeringen en controles vóór verwijdering toegevoegd. Podman is expliciet een gedeeltelijke oefenomgeving.
- Fusion: extra oefenpakketten en services toegevoegd; onbemande installatie vereist een expliciet wachtwoord. Reeds gebruikte oefendisks gelden niet als mislukte eerste installatie.
- Cloudbuilders: unieke labnamen, bewaarde status, expliciete sleutels, beperkte SSH-toegang en verwijdering van bijgehouden resources toegevoegd. Fouten behouden herstelgegevens. Gedeelde of vooraf aangemaakte resources worden niet als eigen resources verwijderd.

## Gebruik

Lees `scripts/README.md` en `VALIDATION-CORRECTIONS.md`. Gebruik de opdrachten binnen Linux-gasten, behalve expliciet genoemde host-installatiestappen. Een bestaande VM hoeft niet opnieuw te worden gebouwd om de aangepaste labopdrachten te gebruiken.

Het uitgebreide oorspronkelijke controleverslag wordt meegeleverd als `AUDIT-ORIGINAL.txt`; het beschrijft de uitgangsversie, niet nieuwe bevindingen in deze revisie.
