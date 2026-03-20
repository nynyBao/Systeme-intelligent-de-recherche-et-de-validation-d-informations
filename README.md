## 📌 Présentation
Ce projet est un système intelligent de questions-réponses capable de rechercher des informations sur Internet, d’analyser leur fiabilité et de fournir une réponse structurée.  

Il combine du web scraping, du traitement automatique du langage (NLP) et des mesures de similarité pour vérifier la cohérence des informations issues de différentes sources.

L’objectif est de permettre à l’utilisateur d’obtenir :

- un résumé général
- une analyse des faits
- des informations confirmées ou infirmées
- des sources vérifiées
- la possibilité d’exporter les résultats

---

## 🚀 Fonctionnalités
- Recherche automatique d’informations à partir d’une question  
- Analyse du contenu des pages web  
- Vérification de la cohérence entre plusieurs sources  
- Résumé structuré et hiérarchisé  
- Liens cliquables vers les sources  
- Export des résultats en TXT ou PDF  
- Interface simple d’utilisation  

---

## 🛠️ Technologies utilisées
- Python  
- Requests — récupération des pages web  
- BeautifulSoup (BS4) — parsing HTML  
- NLTK / TextBlob — traitement du langage naturel  
- Scikit-learn — vectorisation et similarité entre textes  
- JSON — stockage des résultats et métadonnées  
- Regex (re) — nettoyage et normalisation du texte  
- Logging — suivi des opérations  

Architecture modulaire (scraping, NLP, validation, interface)

---

## 🔑 Pré-requis
Avant de lancer l’application, vous devez ajouter vos clés API dans le fichier `code.py` :

- Clé API Tavily (ligne 22)  
- Clé API Mistral (ligne 23)  

Les liens pour obtenir les clés sont indiqués dans le dépôt GitHub.

---

## 📦 Installation

Cloner le dépôt :
    git clone https://github.com/nynyBao/Systeme-intelligent-de-recherche-et-de-validation-d-informations.git

Installer les dépendances :
    pip install -r requirements.txt

Ajouter vos clés API dans `code.py`.

Lancer l’application :
    python code.py

---

## 🎯 Utilisation
1. Saisir une question dans le champ prévu  
2. Cliquer sur **Recherche**  
3. Lire l’analyse générée :
   - Résumé général  
   - Analyse des faits  
   - Informations confirmées / infirmées  
   - Sources vérifiées  
4. Cliquer sur un lien pour ouvrir la source  
5. Exporter le résultat en TXT ou PDF  

---

## 📂 Structure du projet
    code.py            # Script principal
    README.md          # Documentation
    main.tex           # Rapport LaTeX
    assets/            # (optionnel) ressources

---

## 👤 Auteurs
- Ny Avotiana  
- Sahouda
