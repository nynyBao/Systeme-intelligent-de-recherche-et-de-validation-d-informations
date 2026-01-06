import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox

import re
import requests
import webbrowser
import json

from tavily import TavilyClient

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch

# ==============================
# CONFIGURATION GÉNÉRALE
# ==============================

CLES_TAVILY = "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"
CLES_MISTRAL = "SxPUgCYNxcS0a0jFsEzaOq3Opqc8CFth"
URL_API_MISTRAL = "https://api.mistral.ai/v1/chat/completions"

client_tavily = TavilyClient(api_key=CLES_TAVILY)

DOMAINES_FIABLES = [
    "linkedin.com", "wikipedia.org", "gouv.fr", "gov", "edu", "univ", "cnrs.fr"
]

# Références globales sur l'interface principale
application = None
zone_sortie = None
champ_question = None

# ==============================
# FONCTIONS UTILITAIRES
# ==============================

def generer_verdict_fiabilite(score, nb_fiables, nb_total):
    """
    Génère un verdict global (texte) à partir d'un score de fiabilité
    et du nombre de sources fiables.
    """
    if nb_total == 0:
        return "❌ FAUX (aucune source disponible)"
    if nb_fiables >= 2 and score >= 60:
        return "✅ CONFIRMÉ par des sources fiables"
    if nb_fiables == 0:
        return "❌ FAUX (sources non fiables)"
    return "⚠️ NON PROUVÉ (informations insuffisantes)"


def est_question_fermee(texte):
    """
    Renvoie True si la question ressemble à une question fermée
    (affirmation à vérifier), False sinon.
    """
    texte_min = texte.strip().lower()
    if texte_min.startswith("est-ce que") or texte_min.startswith("est ce que"):
        return True

    motifs = [
        "est-il vrai que",
        "est il vrai que",
        "a-t-il",
        "a t il",
        "a-t elle",
        "a t elle",
        "peut-on dire que",
        "peut on dire que",
    ]
    return any(motif in texte_min for motif in motifs)


def est_url_valide(url):
    """Vérifie que l'URL utilise bien le protocole HTTPS."""
    return url.startswith("https://")


def est_url_de_confiance(url):
    """Vérifie si l'URL appartient à un domaine de confiance."""
    return any(domaine in url for domaine in DOMAINES_FIABLES)


def est_url_accessible(url):
    """Teste rapidement si l'URL répond avec un code 200."""
    try:
        reponse = requests.head(url, timeout=5, allow_redirects=True, verify=True)
        return reponse.status_code == 200
    except Exception:
        return False

# ==============================
# 1. RECHERCHE INTERNET (TAVILY)
# ==============================

def rechercher_sur_internet(requete):
    """
    Envoie une requête de recherche à Tavily et retourne la liste
    des résultats structurés.
    """
    try:
        resultats = client_tavily.search(
            query=requete,
            max_results=5,
            include_domains=None
        )
        return resultats["results"]
    except Exception as e:
        return [{"error": str(e)}]

# ==============================
# 2. ANALYSE IA (MISTRAL)
# ==============================

def demander_analyse_mistral(question):
    """
    Envoie la question et les résultats web à l'API Mistral pour obtenir
    une analyse structurée, avec une conclusion explicite VRAI ou FAUX.
    """
    resultats_web = rechercher_sur_internet(question)

    en_tetes = {
        "Authorization": f"Bearer {CLES_MISTRAL}",
        "Content-Type": "application/json"
    }

    donnees = {
        "model": "mistral-small-latest",
        "messages": [
            {
                "role": "system",
                "content": """
Tu es un assistant expert en vérification d'informations.
Tu travailles uniquement à partir des résultats de recherche ci-dessous.
Tu n'inventes jamais de faits.
À la fin de ton analyse, tu dois OBLIGATOIREMENT fournir
une conclusion explicite parmi les deux suivantes :
- VRAI
- FAUX
Tu dois choisir UNE seule option, sans ambiguïté.
Ta réponse se termine toujours par une ligne :
Conclusion : VRAI
ou
Conclusion : FAUX

Structure la réponse en sections claires avec des emojis :
- 📋 Résumé général
- 🔍 Analyse des faits
- ✅ Ce qui est confirmé / ❌ Ce qui est infirmé
- 🔗 Sources vérifiées

Utilise des emojis pour rendre la lecture plus agréable.
Mets en gras les points importants avec **texte**.
"""
            },
            {
                "role": "user",
                "content": f"""
Voici les résultats trouvés sur Internet :
{json.dumps(resultats_web, indent=2, ensure_ascii=False)}

Question : {question}
Analyse ces informations et répond de façon rigoureuse.
"""
            },
        ],
    }

    try:
        reponse = requests.post(URL_API_MISTRAL, json=donnees, headers=en_tetes)
        resultat = reponse.json()
        return resultat["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Erreur API : {e}"

# ==============================
# FORMATAGE DU TEXTE DANS TKINTER
# ==============================

def formater_texte_widget(widget, texte):
    widget.delete("1.0", tk.END)
    widget.config(state=tk.NORMAL)

    motif_url = re.compile(r'(https?://[^\s]+)')
    motif_gras = re.compile(r'\*\*(.+?)\*\*')
    motif_section = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)

    lignes = texte.split("\n")

    for ligne in lignes:
        if not ligne.strip():
            widget.insert(tk.END, "\n")
            continue

        correspondance_section = motif_section.match(ligne)
        if correspondance_section:
            niveau = len(correspondance_section.group(1))
            titre = correspondance_section.group(2).strip()

            widget.insert(tk.END, "\n")

            if niveau == 1:
                widget.insert(tk.END, f"{'='*60}\n", "separator")
                widget.insert(tk.END, f"{titre}\n", "title_h1")
                widget.insert(tk.END, f"{'='*60}\n", "separator")
            elif niveau == 2:
                widget.insert(tk.END, f"{'─'*50}\n", "separator_light")
                widget.insert(tk.END, f"{titre}\n", "title_h2")
                widget.insert(tk.END, f"{'─'*50}\n", "separator_light")
            else:
                widget.insert(tk.END, f"▸ {titre}\n", "title_h3")

            widget.insert(tk.END, "\n")
            continue

        traiter_ligne_formatee(widget, ligne, motif_url, motif_gras)
        widget.insert(tk.END, "\n")


def traiter_ligne_formatee(widget, ligne, motif_url, motif_gras):
    if "Résumé général" in ligne:
        def reduire_bloc_gras(correspondance):
            contenu = correspondance.group(1)
            if len(contenu) > 40:
                return contenu
            return f"**{contenu}**"

        ligne = motif_gras.sub(reduire_bloc_gras, ligne)

    segments = motif_url.split(ligne)
    for segment in segments:
        if motif_url.match(segment):
            formater_url(widget, segment)
        else:
            appliquer_texte_gras(widget, segment, motif_gras)


def appliquer_texte_gras(widget, texte, motif_gras):
    morceaux = motif_gras.split(texte)
    i = 0
    while i < len(morceaux):
        if i % 2 == 0:
            if morceaux[i]:
                widget.insert(tk.END, morceaux[i], "normal")
        else:
            if morceaux[i]:
                widget.insert(tk.END, morceaux[i], "bold")
        i += 1


def formater_url(widget, url):
    if est_url_valide(url) and est_url_de_confiance(url):
        if est_url_accessible(url):
            widget.insert(tk.END, "🔗 ", "emoji")
            widget.insert(tk.END, url, ("url", "clickable"))
        else:
            widget.insert(tk.END, "⚠️ Lien inaccessible : ", "warning")
            widget.insert(tk.END, url, "warning_text")
    else:
        widget.insert(tk.END, "⚠️ Source non fiable : ", "warning")
        widget.insert(tk.END, url, "warning_text")

# ==============================
# GESTION DU CLIC SUR LES LIENS
# ==============================

def ouvrir_url(widget, evenement):
    index = widget.index(f"@{evenement.x},{evenement.y}")
    tags = widget.tag_names(index)
    if "url" in tags:
        ligne = widget.get(index + " linestart", index + " lineend")
        correspondance = re.search(r'https?://[^\s]+', ligne)
        if correspondance:
            webbrowser.open(correspondance.group(0))

# ==============================
# EXPORT TXT
# ==============================

def exporter_txt():
    contenu = zone_sortie.get("1.0", tk.END).strip()
    if not contenu:
        messagebox.showwarning("Attention", "Aucun contenu à sauvegarder.")
        return

    chemin_fichier = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Fichier texte", "*.txt")]
    )
    if not chemin_fichier:
        return

    question = champ_question.get().strip()

    with open(chemin_fichier, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("ASSISTANT WEB IA – RECHERCHE FIABLE\n")
        f.write("=" * 60 + "\n\n")
        f.write("Question :\n")
        f.write(question + "\n\n")
        f.write(contenu)

    messagebox.showinfo("Succès", "Fichier TXT sauvegardé avec succès !")

# ==============================
# EXPORT PDF
# ==============================

def exporter_pdf():
    contenu = zone_sortie.get("1.0", tk.END).strip()
    if not contenu:
        messagebox.showwarning("Attention", "Aucun contenu à sauvegarder.")
        return

    chemin_fichier = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("Fichier PDF", "*.pdf")]
    )
    if not chemin_fichier:
        return

    doc = SimpleDocTemplate(
        chemin_fichier,
        pagesize=A4,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )

    histoire = []

    styles = getSampleStyleSheet()
    style_titre = ParagraphStyle(
        "TitrePrincipal",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#243447"),
        spaceAfter=30,
        alignment=1
    )
    style_section = ParagraphStyle(
        "Section",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#55D5E0"),
        spaceAfter=12,
        spaceBefore=12,
        leftIndent=10
    )
    style_normal = ParagraphStyle(
        "TexteNormal",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#243447"),
        spaceAfter=8,
        leftIndent=15
    )
    style_lien = ParagraphStyle(
        "TexteLien",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#F6B12D"),
        spaceAfter=4,
        leftIndent=15
    )

    texte_titre = "✦ ASSISTANT WEB IA – RECHERCHE FIABLE ✦"
    histoire.append(Paragraph(texte_titre, style_titre))
    histoire.append(Spacer(1, 0.2*inch))

    question = champ_question.get().strip()
    en_tete_question = Paragraph("❯ QUESTION POSÉE :", style_section)
    histoire.append(en_tete_question)

    texte_question = Paragraph(question, style_normal)
    histoire.append(texte_question)
    histoire.append(Spacer(1, 0.3*inch))

    donnees_ligne = [["_" * 100]]
    tableau_ligne = Table(donnees_ligne, colWidths=[6.5*inch])
    tableau_ligne.setStyle(TableStyle([
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#55D5E0")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    histoire.append(tableau_ligne)
    histoire.append(Spacer(1, 0.2*inch))

    remplacements_emoji = {
        "🔍": "➤",
        "📋": "▣",
        "✅": "✓",
        "❌": "✗",
        "⚠️": "⚠",
        "🔗": "⟶",
        "💬": "▸",
        "📊": "▤",
        "🤖": "◆",
        "📄": "▢",
        "📑": "▣",
    }

    sources = []
    dans_section_sources = False
    dans_resume_general = False

    lignes_pretraitees = []
    for ligne in contenu.split("\n"):
        lp = ligne.strip()
        if not lp:
            lignes_pretraitees.append("")
            continue
        for emoji, symbole in remplacements_emoji.items():
            lp = lp.replace(emoji, symbole)
        lignes_pretraitees.append(lp)

    compteur_source = 1
    for lp in lignes_pretraitees:
        if not lp:
            histoire.append(Spacer(1, 0.1*inch))
            continue

        if "Résumé général" in lp:
            histoire.append(Paragraph(lp, style_section))
            dans_resume_general = True
            continue

        if dans_resume_general:
            lp_clean = lp.replace("**", "")
            histoire.append(Paragraph(lp_clean, style_normal))
            dans_resume_general = False
            continue

        if "Sources vérifiées" in lp:
            dans_section_sources = True
            histoire.append(Paragraph(lp, style_section))
            continue

        if dans_section_sources and ("http://" in lp or "https://" in lp):
            match = re.search(r"https?://[^\s\)]*", lp)
            url = match.group(0) if match else lp
            label_source = f"Source {compteur_source}"
            texte_source = f"{label_source} : {url}"
            histoire.append(Paragraph(texte_source, style_lien))
            sources.append((compteur_source, url))
            compteur_source += 1
            continue

        for num, _url in sources:
            tag = f"Source {num}"
            if tag in lp:
                lp = lp.replace(tag, f"{tag}")

        if any(mot in lp for mot in ["Analyse", "confirmé", "infirmé", "VRAI", "FAUX", "NON PROUVÉ", "Conclusion"]):
            histoire.append(Paragraph(lp, style_section))
        elif "**" in lp:
            lp_clean = lp.replace("**", "")
            histoire.append(Paragraph(lp_clean, style_normal))
        else:
            histoire.append(Paragraph(lp, style_normal))

    histoire.append(Spacer(1, 0.5*inch))

    style_pied = ParagraphStyle(
        "PiedDePage",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#6b7280"),
        alignment=1
    )

    pied = Paragraph(
        "─────────────────────────────────────Généré par Assistant Web IA • Powered by Mistral AI & Tavily Search",
        style_pied
    )
    histoire.append(pied)

    doc.build(histoire)

    messagebox.showinfo("Succès", "Fichier PDF sauvegardé avec succès !")

# ==============================
# ENVOI DE LA QUESTION
# ==============================

def lors_envoi_question():
    question = champ_question.get().strip()
    if not question:
        messagebox.showwarning("Attention", "Veuillez entrer une question.")
        return

    if not est_question_fermee(question):
        messagebox.showwarning(
            "Format de question",
            "Pour obtenir une conclusion VRAI / FAUX, la question doit être une "
            "affirmation à vérifier (ex : \"Est-il vrai que ... ?\", \"X a-t-il fait Y ?\")."
        )
        return

    zone_sortie.delete("1.0", tk.END)
    zone_sortie.insert(tk.END, "🔄 Recherche en cours...\n", "loading")
    zone_sortie.update()

    reponse = demander_analyse_mistral(question)

    if "Conclusion" in reponse:
        parties = reponse.split("Conclusion")
        corps = "Conclusion".join(parties[:-1])
        derniere = parties[-1]

        if "VRAI" in derniere.upper():
            conclusion = "Conclusion : VRAI"
        elif "FAUX" in derniere.upper():
            conclusion = "Conclusion : FAUX"
        else:
            conclusion = "Conclusion : FAUX"

        reponse = corps.strip() + "\n" + conclusion

    formater_texte_widget(zone_sortie, reponse)

# ==============================
# INTERFACE PRINCIPALE
# ==============================

def creer_interface_principale():
    global application, zone_sortie, champ_question

    application = tk.Tk()
    application.title("Assistant Web IA")
    application.geometry("1100x800")
    application.configure(bg="#1a2633")

    # Barre latérale
    barre_laterale = tk.Frame(application, bg="#161f2b", width=280)
    barre_laterale.pack(side=tk.LEFT, fill=tk.Y)
    barre_laterale.pack_propagate(False)

    # Logo / titre
    cadre_logo = tk.Frame(barre_laterale, bg="#161f2b")
    cadre_logo.pack(pady=30, padx=20)

    etiquette_logo = tk.Label(
        cadre_logo,
        text="🤖",
        font=("Arial", 48),
        bg="#161f2b",
        fg="#55D5E0"
    )
    etiquette_logo.pack()

    titre_barre = tk.Label(
        cadre_logo,
        text="Assistant Web IA",
        font=("Arial", 16, "bold"),
        bg="#161f2b",
        fg="#FFFFFF",
        justify=tk.CENTER
    )
    titre_barre.pack(pady=10)

    separateur1 = tk.Frame(barre_laterale, bg="#2F4558", height=2)
    separateur1.pack(fill=tk.X, padx=20, pady=20)

    # Infos
    cadre_infos = tk.Frame(barre_laterale, bg="#161f2b")
    cadre_infos.pack(pady=20, padx=20, fill=tk.X)

    etiquette_info1 = tk.Label(
        cadre_infos,
        text="✅ Sources vérifiées",
        font=("Arial", 11),
        bg="#161f2b",
        fg="#55D5E0",
        anchor=tk.W
    )
    etiquette_info1.pack(fill=tk.X, pady=5)

    etiquette_info2 = tk.Label(
        cadre_infos,
        text="🔍 Recherche en temps réel",
        font=("Arial", 11),
        bg="#161f2b",
        fg="#55D5E0",
        anchor=tk.W
    )
    etiquette_info2.pack(fill=tk.X, pady=5)

    etiquette_info3 = tk.Label(
        cadre_infos,
        text="🤖 Analyse par IA",
        font=("Arial", 11),
        bg="#161f2b",
        fg="#55D5E0",
        anchor=tk.W
    )
    etiquette_info3.pack(fill=tk.X, pady=5)

    separateur2 = tk.Frame(barre_laterale, bg="#2F4558", height=2)
    separateur2.pack(fill=tk.X, padx=20, pady=20)

    # Export
    etiquette_export = tk.Label(
        barre_laterale,
        text="📁 Exporter",
        font=("Arial", 12, "bold"),
        bg="#161f2b",
        fg="#FFFFFF"
    )
    etiquette_export.pack(pady=(10, 15))

    bouton_export_txt = tk.Button(
        barre_laterale,
        text="📄 Format TXT",
        font=("Arial", 11),
        bg="#2F4558",
        fg="#FFFFFF",
        activebackground="#3a5468",
        activeforeground="#FFFFFF",
        relief=tk.FLAT,
        bd=0,
        cursor="hand2",
        padx=20,
        pady=12,
        anchor=tk.W,
        command=exporter_txt
    )
    bouton_export_txt.pack(fill=tk.X, padx=20, pady=5)

    bouton_export_pdf = tk.Button(
        barre_laterale,
        text="📑 Format PDF",
        font=("Arial", 11),
        bg="#2F4558",
        fg="#FFFFFF",
        activebackground="#3a5468",
        activeforeground="#FFFFFF",
        relief=tk.FLAT,
        bd=0,
        cursor="hand2",
        padx=20,
        pady=12,
        anchor=tk.W,
        command=exporter_pdf
    )
    bouton_export_pdf.pack(fill=tk.X, padx=20, pady=5)

    etiquette_pied = tk.Label(
        barre_laterale,
        text="Powered by Mistral AI\n& Tavily Search",
        font=("Arial", 9),
        bg="#161f2b",
        fg="#6b7280"
    )
    etiquette_pied.pack(side=tk.BOTTOM, pady=20)

    # Zone principale
    zone_principale = tk.Frame(application, bg="#1a2633")
    zone_principale.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    en_tete = tk.Frame(zone_principale, bg="#1e2936", height=100)
    en_tete.pack(fill=tk.X)
    en_tete.pack_propagate(False)

    contenu_en_tete = tk.Frame(en_tete, bg="#1e2936")
    contenu_en_tete.pack(expand=True)

    titre_principal = tk.Label(
        contenu_en_tete,
        text="Assistant Web IA",
        font=("Arial", 26, "bold"),
        bg="#1e2936",
        fg="#FFFFFF"
    )
    titre_principal.pack(pady=(15, 5))

    soustitre = tk.Label(
        contenu_en_tete,
        text="Recherchez, vérifiez et analysez l'information en temps réel",
        font=("Arial", 11),
        bg="#1e2936",
        fg="#9ca3af"
    )
    soustitre.pack()

    conteneur_contenu = tk.Frame(zone_principale, bg="#1a2633")
    conteneur_contenu.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)

    carte_recherche = tk.Frame(conteneur_contenu, bg="#243447", relief=tk.FLAT, bd=0)
    carte_recherche.pack(fill=tk.X, pady=(0, 25))

    interieur_recherche = tk.Frame(carte_recherche, bg="#243447")
    interieur_recherche.pack(fill=tk.X, padx=25, pady=25)

    etiquette_question = tk.Label(
        interieur_recherche,
        text="💬 Quelle est votre question ? ⚠️ Uniquement une question fermée ⚠️",
        font=("Arial", 13, "bold"),
        bg="#243447",
        fg="#55D5E0"
    )
    etiquette_question.pack(anchor=tk.W, pady=(0, 12))

    ligne_saisie = tk.Frame(interieur_recherche, bg="#243447")
    ligne_saisie.pack(fill=tk.X)

    champ_question_local = tk.Entry(
        ligne_saisie,
        font=("Arial", 13),
        bg="#2F4558",
        fg="white",
        insertbackground="#55D5E0",
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0
    )
    champ_question_local.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=14, ipadx=15)

    bouton_envoyer = tk.Button(
        ligne_saisie,
        text="🔍 Rechercher",
        font=("Arial", 12, "bold"),
        bg="#F6B12D",
        fg="#1a2633",
        activebackground="#ffc107",
        activeforeground="#1a2633",
        relief=tk.FLAT,
        bd=0,
        cursor="hand2",
        padx=35,
        command=lors_envoi_question
    )
    bouton_envoyer.pack(side=tk.LEFT, padx=(15, 0), ipady=10)

    carte_resultats = tk.Frame(conteneur_contenu, bg="#243447", relief=tk.FLAT, bd=0)
    carte_resultats.pack(fill=tk.BOTH, expand=True)

    en_tete_resultats = tk.Frame(carte_resultats, bg="#243447")
    en_tete_resultats.pack(fill=tk.X, padx=25, pady=(20, 10))

    etiquette_resultats = tk.Label(
        en_tete_resultats,
        text="📊 Résultats de la recherche",
        font=("Arial", 13, "bold"),
        bg="#243447",
        fg="#FFFFFF"
    )
    etiquette_resultats.pack(anchor=tk.W)

    zone_sortie_local = scrolledtext.ScrolledText(
        carte_resultats,
        font=("Arial", 12),
        bg="#2F4558",
        fg="#FFFFFF",
        insertbackground="#55D5E0",
        wrap=tk.WORD,
        relief=tk.FLAT,
        bd=0,
        highlightthickness=0,
        padx=20,
        pady=20,
        spacing1=5,
        spacing2=4,
        spacing3=5
    )
    zone_sortie_local.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 25))

    globals()["champ_question"] = champ_question_local
    globals()["zone_sortie"] = zone_sortie_local

    # Styles de texte
    try:
        police_emoji = ("Segoe UI Emoji", 12)
    except Exception:
        try:
            police_emoji = ("Apple Color Emoji", 12)
        except Exception:
            police_emoji = ("Arial", 12)

    zone_sortie_local.tag_config("normal", font=("Arial", 12), foreground="#FFFFFF")
    zone_sortie_local.tag_config("bold", font=("Arial", 12, "bold"), foreground="#FFFFFF")
    zone_sortie_local.tag_config("title_h1", font=("Arial", 18, "bold"), foreground="#F6B12D", spacing1=10, spacing3=10)
    zone_sortie_local.tag_config("title_h2", font=("Arial", 15, "bold"), foreground="#55D5E0", spacing1=8, spacing3=8)
    zone_sortie_local.tag_config("title_h3", font=("Arial", 13, "bold"), foreground="#55D5E0", spacing1=5, spacing3=5)
    zone_sortie_local.tag_config("separator", foreground="#F6B12D")
    zone_sortie_local.tag_config("separator_light", foreground="#55D5E0")
    zone_sortie_local.tag_config("url", foreground="#55D5E0", underline=True)
    zone_sortie_local.tag_config("clickable", foreground="#55D5E0", underline=True)
    zone_sortie_local.tag_config("warning", foreground="#FFA726", font=("Arial", 12, "bold"))
    zone_sortie_local.tag_config("warning_text", foreground="#FFA726")
    zone_sortie_local.tag_config("emoji", font=police_emoji)
    zone_sortie_local.tag_config("loading", font=("Arial", 13, "italic"), foreground="#55D5E0")

    zone_sortie_local.tag_bind("url", "<Button-1>", lambda e: ouvrir_url(zone_sortie_local, e))
    zone_sortie_local.tag_bind("url", "<Enter>", lambda e: zone_sortie_local.config(cursor="hand2"))
    zone_sortie_local.tag_bind("url", "<Leave>", lambda e: zone_sortie_local.config(cursor=""))

    champ_question_local.bind("<Return>", lambda e: lors_envoi_question())

    application.mainloop()

# ==============================
# POINT D'ENTRÉE
# ==============================

if __name__ == "__main__":
    creer_interface_principale()
