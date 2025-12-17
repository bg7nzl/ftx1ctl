**Console FTX-1 (ftx1gui)**

***

# Manuel de l'utilisateur de la Console FTX-1

Ce manuel fournit un guide complet pour l'utilisation du logiciel `ftx1gui` pour contrôler l'émetteur-récepteur FTX-1. Il couvre la configuration de la connexion, la gestion des fréquences, les contrôles de transmission et les fonctionnalités avancées de traitement audio.

## 1. Configuration de la connexion (Panneau supérieur)

La section supérieure de l'application est dédiée à l'établissement de la communication avec la radio et les logiciels externes.

### Contrôle CAT (Computer Aided Transceiver)
*   **Port CAT (CAT Port)** : Sélectionne le port COM utilisé pour envoyer des commandes (fréquence, mode, etc.) à la radio.
    *   *Logique par défaut* : Le logiciel recherche automatiquement les ports disponibles. Il donne la priorité aux ports nommés "**Enhanced COM Port**" (courant avec les pilotes Silicon Labs utilisés dans les radios Yaesu). S'il n'est pas trouvé, il utilise par défaut le premier port disponible.
*   **Baud** : Définit la vitesse de communication.
    *   *Défaut* : **38400** bps. Assurez-vous que cela correspond au réglage dans le menu de votre radio (CAT RATE).

### Contrôle PTT (Push-To-Talk)
*   **Port PTT (PTT Port)** : Sélectionne le port COM utilisé pour déclencher la transmission via le signal RTS (Request to Send).
    *   *Logique par défaut* : Donne la priorité aux ports nommés "**Standard COM Port**". Si vous avez deux ports (Enhanced & Standard), le port Standard est généralement utilisé pour la manipulation PTT/CW.
*   **Baud** : Définit la vitesse pour le port PTT (généralement moins critique que le CAT).
    *   *Défaut* : **38400** bps.

### Boutons de connexion
*   **Connecter (Connect)** : Ouvre les ports COM et commence à interroger la radio.
*   **Déconnecter (Disconnect)** : Ferme la connexion et arrête l'interrogation.
*   **Lecture complète (Full Read)** : Force une synchronisation complète de tous les paramètres de la radio vers l'interface utilisateur.
    *   *Note* : Le logiciel programme automatiquement une lecture complète après le réglage des paramètres, mais ce bouton est utile si l'interface utilisateur n'est plus synchronisée.

### Serveur Rigctl (Contrôle réseau)
*   **Port TCP rigctl** : Le numéro de port pour le serveur TCP intégré compatible Hamlib.
    *   *Défaut* : **4532**.
    *   *Utilisation* : Permet à des logiciels tiers (comme WSJT-X, N1MM ou Log4OM) de contrôler la radio *via* cette application en se connectant à `localhost:4532` en utilisant le modèle "Hamlib NET rigctl" (ID de modèle 2).

---

## 2. Fréquence et Mode (Panneau gauche)

### Affichage de la fréquence
*   **Affichage** : Affiche la fréquence actuelle en Hz.

*  **Réglage chiffre par chiffre** : 
    1. Survolez avec le curseur de la souris le chiffre spécifique que vous souhaitez modifier.
    2. **Molette de la souris** : Faites défiler vers le haut pour augmenter la valeur ou vers le bas pour la diminuer.
    3. **Boutons fléchés** : Cliquez sur les petites **flèches haut/bas** situées au-dessus et au-dessous de chaque chiffre pour un ajustement pas à pas.

### Sélection du mode
Une grille de boutons vous permet de changer le mode de fonctionnement.
*   **Mode actif** : Le mode actuellement sélectionné est mis en évidence en **Vert**.
*   **Modes supportés** :
    *   **Rangée 1** : USB, DATA-U, CW-U, RTTY-U, AM, FM, FM-N, C4FM-DN, PSK
    *   **Rangée 2** : LSB, DATA-L, CW-L, RTTY-L, AM-N, DATA-FM, DATA-FM-N, C4FM-VW

---

## 3. Contrôle de transmission (Panneau central)

### PTT (Push-To-Talk)
*   **Bouton Transmettre (Transmit)** : Bascule l'état de transmission de la radio.
    *   **Blanc** : État de réception (RX).
    *   **Rouge** : État de transmission (TX).
    *   *Mécanisme* : Cela bascule le signal RTS sur le **Port PTT** sélectionné.

### Contrôle de puissance
*   **Puissance (W)** : Un curseur pour ajuster la puissance de sortie RF.
*   **Affichage de la valeur** : Affiche la puissance cible en Watts.
*   **Indicateur de type d'appareil** : Affiche la classe de puissance détectée de la radio (par ex., "FIELD", "SPA1").
    *   **FIELD** : Plage 1–10 W.
    *   **SPA1** : Plage 5–100 W.
    *   **Standard** : Plage 1–100 W.

---

## 4. Prétraitement de réception (Panneau central)

Cette section contrôle le gain du récepteur et les paramètres de contrôle automatique de gain (AGC).

### AGC (Contrôle Automatique de Gain)
Contrôle comment la radio gère les variations de force du signal.
*   **Options** : OFF (Arrêt), FAST (Rapide), MID (Moyen), SLOW (Lent), AUTO.
*   **Logique d'affichage** :
    *   Si vous sélectionnez **AUTO**, la radio détermine la meilleure vitesse en fonction du mode actuel (par ex., CW par défaut FAST, SSB par défaut SLOW).
    *   **Indicateur visuel** : Si la radio est en mode AUTO et a sélectionné "MID" en interne, **les deux** boutons `AUTO` et `MID` seront mis en évidence. Cela vous permet de savoir que vous êtes en mode Auto *et* quelle est la vitesse effective actuelle.

### Préampli (Preamp)
Ajuste le gain d'entrée du récepteur pour différentes bandes.
*   **HF/50 MHz** :
    *   **IPO** : Optimisation du point d'interception (Préampli OFF). Idéal pour les environnements à signal fort.
    *   **AMP1** : Préampli à faible gain.
    *   **AMP2** : Préampli à gain élevé.
*   **VHF / UHF** :
    *   **OFF / ON** : Bascule le préampli pour ces bandes.

---

## 5. Contrôle manuel du Notch (Panneau droit/inférieur)

Ce panneau avancé vous permet de visualiser l'audio et de supprimer manuellement les tonalités interférentes (Notch).

### Contrôles
*   **Activer Notch (Enable Notch)** : Case à cocher pour activer le filtre notch manuel sur la radio.
*   **Fréq (Hz)** :
    *   **Zone de saisie** : Tapez une fréquence spécifique (10–3200 Hz) et cliquez sur **Régler (Set)**.
    *   **Actuel (Current)** : Affiche la valeur actuellement active dans la radio.
    *   **Lire (Read)** : Rafraîchit la valeur affichée depuis la radio.

### Waterfall Audio / Spectre
*   **Périphérique d'entrée (Input Device)** : Sélectionne la source audio pour l'affichage du waterfall.
    *   *Logique par défaut* : Le logiciel scanne les périphériques audio et préfère celui contenant "**USB Audio Device**" dans son nom (typique pour les cartes son radio intégrées).
*   **Affichage Waterfall** : Affiche un spectrogramme en temps réel de l'audio reçu.
    *   **Axe X** : Temps (historique défilant).
    *   **Axe Y** : Fréquence audio (0–4000 Hz).
*   **Interaction** :
    *   **Cliquer pour Notch** : Cliquer n'importe où sur le waterfall réglera automatiquement la fréquence du Notch manuel sur cette tonalité.
    *   **Retour visuel** : Deux lignes horizontales rouges apparaissent sur le waterfall pour indiquer la position et la largeur (env. 100 Hz) du filtre notch actif.

---

## 6. Mesures (Panneau inférieur)

Une rangée de barres de mesure fournit une télémétrie en temps réel de la radio. Chaque mesure a une ligne rouge de "seuil" indiquant une valeur nominale ou limite.

| Mesure | Description | Unité | Seuil (Ligne rouge) |
| :--- | :--- | :--- | :--- |
| **S_MAIN** | Force du signal | Unités-S / dB | S9 |
| **COMP** | Niveau de compression vocale | dB | 15 dB |
| **ALC** | Tension de contrôle automatique de niveau | % | 100% |
| **PO** | Puissance de sortie | Watts | 10 W (variable) |
| **SWR** | Rapport d'ondes stationnaires (ROS) | Ratio | 3.0 |
| **IDD** | Courant de drain | Ampères | 2 A |
| **VDD** | Tension d'alimentation | Volts | 13.8 V |

*   **Taux de rafraîchissement** : Les mesures sont mises à jour environ une fois par seconde (par défaut) pour minimiser le trafic du bus CAT.

---

## 7. Dépannage

*   **"Need CAT and PTT ports" (Besoin des ports CAT et PTT)** : Vous devez sélectionner un port COM pour les deux champs. Si vous n'avez qu'un seul câble, vous devrez peut-être sélectionner le même port pour les deux, ou vérifier si votre pilote crée deux ports virtuels (Standard & Enhanced).
*   **Les mesures ne bougent pas** : Assurez-vous que la connexion est active (la barre d'état indique "Connected"). Vérifiez si un autre programme accapare le port COM.
*   **Le waterfall est noir** : Assurez-vous que le bon **Périphérique d'entrée** est sélectionné. Il doit correspondre au périphérique "Line In" ou "Microphone" associé à la connexion USB de votre radio.
*   **Rigctl ne fonctionne pas** : Assurez-vous qu'aucun autre logiciel n'utilise le port 4532. Si vous changez le port dans l'interface utilisateur, mettez à jour votre logiciel/logger externe pour qu'il corresponde.


## 7. Limitations matérielles et étalonnage

### Note importante pour les utilisateurs SPA-1 / Optima
Comme le développeur utilise actuellement la version **FTX-1 Field** (autonome 10W), le système de télémétrie est spécifiquement réglé pour une opération portable à faible puissance.

* **Précision PO (Puissance de sortie)** : L'échelle en watts et la déviation du compteur sont calibrées pour l'ampli interne de 10W. Pour les utilisateurs de 100W, le compteur peut atteindre le plafond prématurément ou afficher une échelle incorrecte.
* **Précision IDD (Courant de drain)** : Le compteur IDD est actuellement calibré pour la consommation typique de l'unité Field (max environ 2A). L'opération à 100W nécessite un courant significativement plus élevé, qui n'est pas encore mappé avec précision dans cette interface.

---

## 8. Note sur l'étalonnage SPA-1 (100W)

Actuellement, ce logiciel est développé et testé en utilisant la version **FTX-1 Field (10W autonome)**. Parce que je n'ai pas l'amplificateur **Optima SPA-1 (100W)** sur mon bureau, les compteurs de **Puissance (PO)** et de **Courant (IDD)** ne sont pas encore entièrement calibrés pour une opération à haute puissance.

**J'ai besoin de votre aide !** Si vous utilisez la configuration Optima SPA-1, le logiciel peut afficher des lectures de puissance et de courant inexactes. Si vous souhaitez m'aider à améliorer cela pour toute la communauté, je vous serais incroyablement reconnaissant si vous pouviez partager quelques photos ou un court clip de l'écran de votre radio montrant les lectures PO et IDD à différents niveaux de puissance.

Vos données m'aideront à affiner les mathématiques derrière ces compteurs afin qu'ils fonctionnent parfaitement pour chaque propriétaire de FTX-1. N'hésitez pas à me contacter via le dépôt du projet !

---
