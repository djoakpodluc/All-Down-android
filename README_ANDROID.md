# 📱 AllDown pour Android — Guide complet

Cette version d'AllDown est écrite en Python (comme la version bureau),
avec le framework **Kivy** qui permet de faire de vraies applications
Android. Pas besoin de connaître Java/Kotlin.

## ⚠️ Différences avec la version bureau

Android ne permet pas d'embarquer ffmpeg aussi simplement qu'un PC. Pour que
la compilation reste fiable, cette version mobile :
- télécharge les vidéos dans un format **déjà prêt à l'emploi** (pas besoin
  de fusionner vidéo + audio),
- récupère l'audio dans son **format d'origine** (m4a/webm/opus) sans le
  convertir en mp3,
- ne peut pas mettre à jour yt-dlp "à chaud" : il faut recompiler une
  nouvelle version de l'app pour ça (contrairement au bureau).

En échange, elle profite de deux avantages propres au mobile :
- **Recevoir un lien directement depuis le bouton "Partager"** de YouTube,
  TikTok, Instagram... (pas besoin de copier-coller !)
- Notifications natives Android, plus fiables que sur Windows.

## 🚀 Obtenir le fichier .apk — méthode recommandée (aucune installation)

Vous n'avez **rien à installer sur votre PC**. La compilation se fait
gratuitement dans le cloud via GitHub Actions.

### Étape 1 — Créer un dépôt GitHub
1. Créez un compte gratuit sur [github.com](https://github.com) si vous n'en
   avez pas.
2. Cliquez sur **"New repository"**, donnez-lui un nom (ex. `alldown-android`),
   laissez-le "Public" ou "Private", cliquez sur **"Create repository"**.

### Étape 2 — Envoyer les fichiers
Sur la page du dépôt fraîchement créé, cliquez sur **"uploading an existing
file"** (ou "Add file" → "Upload files"), puis glissez-déposez **tout le
contenu du dossier `AllDown-Android`** (tous les fichiers, y compris le
dossier `.github` avec ses sous-dossiers). Cliquez sur **"Commit changes"**.

### Étape 3 — Lancer la compilation
1. Allez dans l'onglet **"Actions"** en haut de la page du dépôt.
2. Vous devriez voir "Compiler AllDown.apk" démarrer automatiquement
   (sinon, cliquez dessus puis "Run workflow").
3. Patientez : **20 à 40 minutes** la première fois (les fois suivantes
   sont plus rapides grâce au cache).

### Étape 4 — Télécharger l'APK
1. Une fois le workflow terminé (coche verte ✅), cliquez dessus.
2. Tout en bas de la page, dans la section **"Artifacts"**, téléchargez
   **"AllDown-apk"** (fichier .zip contenant l'APK).
3. Décompressez, transférez le fichier `.apk` sur votre téléphone/tablette
   (par câble USB, ou en vous l'envoyant par email/cloud).
4. Sur Android, ouvrez le fichier .apk pour l'installer. Android va
   probablement vous avertir "source inconnue" : c'est normal pour toute
   application installée hors du Play Store — autorisez l'installation.

## 🖥️ Alternative — compiler vous-même sous Linux/WSL

Si vous préférez tout faire localement (Buildozer ne fonctionne **pas**
nativement sous Windows, il faut WSL — Windows Subsystem for Linux) :

```bash
# Dans un terminal Ubuntu (WSL) ou Linux :
sudo apt update && sudo apt install -y git zip unzip openjdk-17-jdk \
    autoconf libtool pkg-config build-essential cmake libffi-dev libssl-dev
pip install --upgrade buildozer cython==3.0.10
cd AllDown-Android
buildozer android debug
```
L'APK apparaît ensuite dans le dossier `bin/`.

## 🧪 Tester sur votre PC avant de compiler (optionnel)

Cette même application fonctionne aussi sur PC (pratique pour vérifier que
tout marche avant de lancer une compilation de 30 minutes) :
```bash
pip install kivy yt-dlp plyer
python main.py
```

## 📁 Contenu du dossier

| Fichier / dossier              | Rôle                                              |
|----------------------------------|------------------------------------------------------|
| `main.py`                        | Application (logique + interface Kivy)              |
| `common.py`                      | Fonctions partagées (détection de plateforme, etc.) |
| `alldown.kv`                     | Mise en page de l'interface                          |
| `buildozer.spec`                 | Configuration de compilation Android                 |
| `android_intent_filters.xml`      | Permet de recevoir les liens "Partagés"              |
| `icon.png` / `presplash.png`      | Icône et écran de démarrage                          |
| `.github/workflows/build-apk.yml` | Compilation automatique dans le cloud                |

## 🔧 Dépannage

- **Le workflow échoue** : ouvrez le détail du job dans l'onglet Actions,
  le message d'erreur est généralement explicite (dépendance manquante,
  etc.). N'hésitez pas à me montrer une capture, je peux corriger.
- **"Source inconnue" refusée à l'installation** : allez dans
  Paramètres → Sécurité (ou "Applications") de votre Android et autorisez
  l'installation depuis la source utilisée (navigateur, gestionnaire de
  fichiers...).
