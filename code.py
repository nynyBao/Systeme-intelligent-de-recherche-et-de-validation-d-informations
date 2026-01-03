import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox
import re
import requests
import webbrowser
from PIL import Image, ImageTk
import json
from tavily import TavilyClient
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch


# CONFIGURATION

TAVILY_KEY = "Votre_clef_api_tavily_ici"
MISTRAL_KEY = "Votre_clef_api_mistral_ici"

API_URL = "https://api.mistral.ai/v1/chat/completions"
tavily = TavilyClient(api_key=TAVILY_KEY)

TRUSTED_DOMAINS = [
    'linkedin.com', 'wikipedia.org', 'gouv.fr', 'gov', 'edu', 'univ', 'cnrs.fr'
]

def verdict_from_reliability(score, trusted, total):
    if total == 0:
        return "❌ FAUX (aucune source disponible)"

    if trusted >= 2 and score >= 60:
        return "✅ CONFIRMÉ par des sources fiables"

    if trusted == 0:
        return "❌ FAUX (sources non fiables)"

    return "⚠️ NON PROUVÉ (informations insuffisantes)"


# ------------------------------
# VALIDATION URL
# ------------------------------

def is_valid_url(url):
    return url.startswith("https://")

def is_trusted_url(url):
    return any(domain in url for domain in TRUSTED_DOMAINS)

def is_url_accessible(url):
    try:
        r = requests.head(url, timeout=5, allow_redirects=True, verify=True)
        return r.status_code == 200
    except:
        return False

# ------------------------------
# 1. RECHERCHE INTERNET (TAVILY)
# ------------------------------

def search_web(query):
    try:
        results = tavily.search(
            query=query,
            max_results=5,
            include_domains=None
        )
        return results["results"]
    except Exception as e:
        return [{"error": str(e)}]

# ------------------------------
# 2. ANALYSE IA (MISTRAL)
# ------------------------------

def ask_mistral(question):
    web_results = search_web(question)

    headers = {
        "Authorization": f"Bearer {MISTRAL_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "mistral-small-latest",
        "messages": [
            {
                "role": "system",
                "content": """
Tu es un assistant expert en vérification d'informations.
Tu travailles uniquement à partir des résultats de recherche ci-dessous.
Tu n'inventes jamais de faits.
À la fin de ton analyse, tu dois OBLIGATOIREMENT fournir
une conclusion explicite parmi les trois suivantes :
- VRAI
- FAUX
- NON PROUVÉ
Tu dois choisir UNE seule option, sans ambiguïté.
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

{json.dumps(web_results, indent=2, ensure_ascii=False)}

Question : {question}

Analyse ces informations et répond de façon rigoureuse.
                """
            }
        ]
    }

    try:
        response = requests.post(API_URL, json=data, headers=headers)
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ Erreur API : {e}"

# ------------------------------
# FORMATAGE DU TEXTE AMÉLIORÉ
# ------------------------------

def format_text_in_widget(widget, text):
    widget.delete("1.0", tk.END)
    widget.config(state=tk.NORMAL)

    # Patterns de détection
    url_pattern = re.compile(r'(https?://[^\s]+)')
    bold_pattern = re.compile(r'\*\*(.+?)\*\*')
    section_pattern = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)
    
    # Liste des emojis courants à détecter
    emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF]|[\u2600-\u26FF]|[\u2700-\u27BF]')

    lines = text.split('\n')
    
    for line in lines:
        if not line.strip():
            widget.insert(tk.END, "\n")
            continue
        
        # Détection des titres de section (## ou ###)
        section_match = section_pattern.match(line)
        if section_match:
            level = len(section_match.group(1))
            title = section_match.group(2).strip()
            
            widget.insert(tk.END, "\n")
            if level == 1:
                widget.insert(tk.END, f"{'='*60}\n", "separator")
                widget.insert(tk.END, f"{title}\n", "title_h1")
                widget.insert(tk.END, f"{'='*60}\n", "separator")
            elif level == 2:
                widget.insert(tk.END, f"{'─'*50}\n", "separator_light")
                widget.insert(tk.END, f"{title}\n", "title_h2")
                widget.insert(tk.END, f"{'─'*50}\n", "separator_light")
            else:
                widget.insert(tk.END, f"▸ {title}\n", "title_h3")
            widget.insert(tk.END, "\n")
            continue
        
        # Traiter le texte avec formatage
        process_line_formatting(widget, line, url_pattern, bold_pattern)
        widget.insert(tk.END, "\n")

def process_line_formatting(widget, line, url_pattern, bold_pattern):
    """Traite une ligne avec tous les formatages (gras, URLs, emojis)"""
    
    # Séparer les URLs du reste
    segments = url_pattern.split(line)
    
    for segment in segments:
        if url_pattern.match(segment):
            # C'est une URL
            format_url(widget, segment)
        else:
            # Traiter le texte normal avec le gras
            format_bold_text(widget, segment, bold_pattern)

def format_bold_text(widget, text, bold_pattern):
    """Applique le formatage gras au texte"""
    parts = bold_pattern.split(text)
    
    i = 0
    while i < len(parts):
        if i % 2 == 0:
            # Texte normal
            if parts[i]:
                widget.insert(tk.END, parts[i], "normal")
        else:
            # Texte en gras
            if parts[i]:
                widget.insert(tk.END, parts[i], "bold")
        i += 1

def format_url(widget, url):
    """Formate et valide une URL"""
    if is_valid_url(url) and is_trusted_url(url):
        if is_url_accessible(url):
            widget.insert(tk.END, "🔗 ", "emoji")
            widget.insert(tk.END, url, ("url", "clickable"))
        else:
            widget.insert(tk.END, "⚠️ Lien inaccessible : ", "warning")
            widget.insert(tk.END, url, "warning_text")
    else:
        widget.insert(tk.END, "⚠️ Source non fiable : ", "warning")
        widget.insert(tk.END, url, "warning_text")

# ------------------------------
# OUVERTURE DES LIENS
# ------------------------------

def open_url(widget, event):
    index = widget.index(f"@{event.x},{event.y}")
    tags = widget.tag_names(index)
    if "url" in tags:
        line = widget.get(index + " linestart", index + " lineend")
        match = re.search(r'https?://[^\s]+', line)
        if match:
            webbrowser.open(match.group(0))

# ------------------------------
# EXPORT TXT / PDF
# ------------------------------

def export_txt():
    content = output_box.get("1.0", tk.END).strip()
    if not content:
        messagebox.showwarning("Attention", "Aucun contenu à sauvegarder.")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Fichier texte", "*.txt")]
    )

    if not file_path:
        return

    question = question_entry.get().strip()

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("ASSISTANT WEB IA – RECHERCHE FIABLE\n")
        f.write("=" * 60 + "\n\n")
        f.write("Question :\n")
        f.write(question + "\n\n")
        f.write(content)

    messagebox.showinfo("Succès", "Fichier TXT sauvegardé avec succès !")

def export_pdf():
    content = output_box.get("1.0", tk.END).strip()
    if not content:
        messagebox.showwarning("Attention", "Aucun contenu à sauvegarder.")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("Fichier PDF", "*.pdf")]
    )

    if not file_path:
        return

    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import inch

    doc = SimpleDocTemplate(file_path, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()

    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#243447'),
        spaceAfter=30,
        alignment=1  # Centré
    )

    # Style pour les sections
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#55D5E0'),
        spaceAfter=12,
        spaceBefore=12,
        leftIndent=10
    )

    # Style pour le texte normal
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#243447'),
        spaceAfter=8,
        leftIndent=15
    )

    # Style pour le texte en gras
    bold_style = ParagraphStyle(
        'BoldStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#243447'),
        spaceAfter=8,
        leftIndent=15,
        fontName='Helvetica-Bold'
    )

    # Titre principal avec symboles au lieu d'emojis
    title_text = "⚡ ASSISTANT WEB IA – RECHERCHE FIABLE ⚡"
    story.append(Paragraph(title_text, title_style))
    story.append(Spacer(1, 0.2*inch))

    # Question posée avec symbole
    question = question_entry.get().strip()
    question_header = Paragraph("<b>❯ QUESTION POSÉE :</b>", section_style)
    story.append(question_header)
    
    question_text = Paragraph(question, normal_style)
    story.append(question_text)
    story.append(Spacer(1, 0.3*inch))

    # Ligne de séparation
    line_data = [['_' * 100]]
    line_table = Table(line_data, colWidths=[6.5*inch])
    line_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#55D5E0')),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 0.2*inch))

    # Traitement du contenu avec remplacement des emojis
    emoji_replacements = {
        '🔍': '➤',
        '📋': '▣',
        '✅': '✓',
        '❌': '✗',
        '⚠️': '⚠',
        '🔗': '⟶',
        '💬': '▸',
        '📊': '▤',
        '🤖': '◆',
        '📄': '▢',
        '📑': '▣'
    }

    for line in content.split("\n"):
        line_clean = line.strip()
        
        if not line_clean:
            story.append(Spacer(1, 0.1*inch))
            continue

        # Remplacer les emojis par des symboles
        for emoji, symbol in emoji_replacements.items():
            line_clean = line_clean.replace(emoji, symbol)

        # Détection des sections importantes
        if any(keyword in line_clean for keyword in ["Résumé", "Analyse", "confirmé", "infirmé", "Sources", "VRAI", "FAUX", "NON PROUVÉ"]):
            para = Paragraph(f"<b>{line_clean}</b>", section_style)
            story.append(para)
        # Détection du texte en gras
        elif "**" in line_clean:
            # Remplacer ** par des balises HTML
            line_html = line_clean.replace("**", "<b>").replace("**", "</b>")
            # Correction si nombre impair de **
            if line_html.count("<b>") > line_html.count("</b>"):
                line_html += "</b>"
            para = Paragraph(line_html, normal_style)
            story.append(para)
        else:
            para = Paragraph(line_clean, normal_style)
            story.append(para)

    # Footer
    story.append(Spacer(1, 0.5*inch))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#6b7280'),
        alignment=1
    )
    footer = Paragraph("─────────────────────────────────────<br/>Généré par Assistant Web IA • Powered by Mistral AI & Tavily Search", footer_style)
    story.append(footer)

    # Construire le PDF
    doc.build(story)
    messagebox.showinfo("Succès", "Fichier PDF sauvegardé avec succès !")

def wrap_text(text, max_chars):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 <= max_chars:
            current_line += word + " "
        else:
            lines.append(current_line)
            current_line = word + " "

    if current_line:
        lines.append(current_line)

    return lines

# ------------------------------
# ACTION DU BOUTON
# ------------------------------

def on_send():
    question = question_entry.get().strip()
    if not question:
        messagebox.showwarning("Attention", "Veuillez entrer une question.")
        return
    
    # Afficher un message de chargement
    output_box.delete("1.0", tk.END)
    output_box.insert(tk.END, "🔄 Recherche en cours...\n", "loading")
    output_box.update()
    
    response = ask_mistral(question)
    format_text_in_widget(output_box, response)

# ------------------------------
# INTERFACE TKINTER ULTRA-MODERNE
# ------------------------------

app = tk.Tk()
app.title("Assistant Web IA – Recherche Fiable")
app.geometry("1100x800")
app.configure(bg="#1a2633")

# ============= SIDEBAR GAUCHE =============
sidebar = tk.Frame(app, bg="#161f2b", width=280)
sidebar.pack(side=tk.LEFT, fill=tk.Y)
sidebar.pack_propagate(False)

# Logo et titre sidebar
logo_frame = tk.Frame(sidebar, bg="#161f2b")
logo_frame.pack(pady=30, padx=20)

logo_label = tk.Label(
    logo_frame,
    text="🤖",
    font=("Arial", 48),
    bg="#161f2b",
    fg="#55D5E0"
)
logo_label.pack()

sidebar_title = tk.Label(
    logo_frame,
    text="AI Research\nAssistant",
    font=("Arial", 16, "bold"),
    bg="#161f2b",
    fg="#FFFFFF",
    justify=tk.CENTER
)
sidebar_title.pack(pady=10)

# Séparateur
sep1 = tk.Frame(sidebar, bg="#2F4558", height=2)
sep1.pack(fill=tk.X, padx=20, pady=20)

# Statistiques / Info
stats_frame = tk.Frame(sidebar, bg="#161f2b")
stats_frame.pack(pady=20, padx=20, fill=tk.X)

stat_label1 = tk.Label(
    stats_frame,
    text="✅ Sources vérifiées",
    font=("Arial", 11),
    bg="#161f2b",
    fg="#55D5E0",
    anchor=tk.W
)
stat_label1.pack(fill=tk.X, pady=5)

stat_label2 = tk.Label(
    stats_frame,
    text="🔍 Recherche en temps réel",
    font=("Arial", 11),
    bg="#161f2b",
    fg="#55D5E0",
    anchor=tk.W
)
stat_label2.pack(fill=tk.X, pady=5)

stat_label3 = tk.Label(
    stats_frame,
    text="🤖 Analyse par IA",
    font=("Arial", 11),
    bg="#161f2b",
    fg="#55D5E0",
    anchor=tk.W
)
stat_label3.pack(fill=tk.X, pady=5)

# Séparateur
sep2 = tk.Frame(sidebar, bg="#2F4558", height=2)
sep2.pack(fill=tk.X, padx=20, pady=20)

# Boutons d'export dans sidebar
export_sidebar_label = tk.Label(
    sidebar,
    text="📁 Exporter",
    font=("Arial", 12, "bold"),
    bg="#161f2b",
    fg="#FFFFFF"
)
export_sidebar_label.pack(pady=(10, 15))

btn_txt_sidebar = tk.Button(
    sidebar,
    text="📄  Format TXT",
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
    command=export_txt
)
btn_txt_sidebar.pack(fill=tk.X, padx=20, pady=5)

btn_pdf_sidebar = tk.Button(
    sidebar,
    text="📑  Format PDF",
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
    command=export_pdf
)
btn_pdf_sidebar.pack(fill=tk.X, padx=20, pady=5)

# Footer sidebar
footer_label = tk.Label(
    sidebar,
    text="Powered by Mistral AI\n& Tavily Search",
    font=("Arial", 9),
    bg="#161f2b",
    fg="#6b7280"
)
footer_label.pack(side=tk.BOTTOM, pady=20)

# ============= ZONE PRINCIPALE =============
main_area = tk.Frame(app, bg="#1a2633")
main_area.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# Header moderne avec gradient simulé
header_frame = tk.Frame(main_area, bg="#1e2936", height=100)
header_frame.pack(fill=tk.X)
header_frame.pack_propagate(False)

header_content = tk.Frame(header_frame, bg="#1e2936")
header_content.pack(expand=True)

title_main = tk.Label(
    header_content,
    text="Assistant Web IA",
    font=("Arial", 26, "bold"),
    bg="#1e2936",
    fg="#FFFFFF"
)
title_main.pack(pady=(15, 5))

subtitle = tk.Label(
    header_content,
    text="Recherchez, vérifiez et analysez l'information en temps réel",
    font=("Arial", 11),
    bg="#1e2936",
    fg="#9ca3af"
)
subtitle.pack()

# Container pour le contenu avec padding
content_container = tk.Frame(main_area, bg="#1a2633")
content_container.pack(fill=tk.BOTH, expand=True, padx=40, pady=30)

# Zone de recherche moderne avec card style
search_card = tk.Frame(content_container, bg="#243447", relief=tk.FLAT, bd=0)
search_card.pack(fill=tk.X, pady=(0, 25))

# Padding interne
search_inner = tk.Frame(search_card, bg="#243447")
search_inner.pack(fill=tk.X, padx=25, pady=25)

label_question = tk.Label(
    search_inner,
    text="💬  Quelle est votre question ?",
    font=("Arial", 13, "bold"),
    bg="#243447",
    fg="#55D5E0"
)
label_question.pack(anchor=tk.W, pady=(0, 12))

# Frame pour input et bouton côte à côte
input_row = tk.Frame(search_inner, bg="#243447")
input_row.pack(fill=tk.X)

question_entry = tk.Entry(
    input_row,
    font=("Arial", 13),
    bg="#2F4558",
    fg="white",
    insertbackground="#55D5E0",
    relief=tk.FLAT,
    bd=0,
    highlightthickness=0
)
question_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=14, ipadx=15)

send_button = tk.Button(
    input_row,
    text="🔍  Rechercher",
    font=("Arial", 12, "bold"),
    bg="#F6B12D",
    fg="#1a2633",
    activebackground="#ffc107",
    activeforeground="#1a2633",
    relief=tk.FLAT,
    bd=0,
    cursor="hand2",
    padx=35,
    command=on_send
)
send_button.pack(side=tk.LEFT, padx=(15, 0), ipady=10)

# Zone de résultat moderne avec card style
result_card = tk.Frame(content_container, bg="#243447", relief=tk.FLAT, bd=0)
result_card.pack(fill=tk.BOTH, expand=True)

# Header de la carte résultat
result_header = tk.Frame(result_card, bg="#243447")
result_header.pack(fill=tk.X, padx=25, pady=(20, 10))

result_title = tk.Label(
    result_header,
    text="📊  Résultats de la recherche",
    font=("Arial", 13, "bold"),
    bg="#243447",
    fg="#FFFFFF"
)
result_title.pack(anchor=tk.W)

# Scrolled text moderne
output_box = scrolledtext.ScrolledText(
    result_card,
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
output_box.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 25))

# Configuration des styles de texte avec police supportant les emojis
try:
    emoji_font = ("Segoe UI Emoji", 12)  # Windows
except:
    try:
        emoji_font = ("Apple Color Emoji", 12)  # macOS
    except:
        emoji_font = ("Arial", 12)  # Fallback

output_box.tag_config("normal", font=("Arial", 12), foreground="#FFFFFF")
output_box.tag_config("bold", font=("Arial", 12, "bold"), foreground="#FFFFFF")
output_box.tag_config("title_h1", font=("Arial", 18, "bold"), foreground="#F6B12D", spacing1=10, spacing3=10)
output_box.tag_config("title_h2", font=("Arial", 15, "bold"), foreground="#55D5E0", spacing1=8, spacing3=8)
output_box.tag_config("title_h3", font=("Arial", 13, "bold"), foreground="#55D5E0", spacing1=5, spacing3=5)
output_box.tag_config("separator", foreground="#F6B12D")
output_box.tag_config("separator_light", foreground="#55D5E0")
output_box.tag_config("url", foreground="#55D5E0", underline=True)
output_box.tag_config("clickable", foreground="#55D5E0", underline=True)
output_box.tag_config("warning", foreground="#FFA726", font=("Arial", 12, "bold"))
output_box.tag_config("warning_text", foreground="#FFA726")
output_box.tag_config("emoji", font=emoji_font)  # Police spéciale pour emojis
output_box.tag_config("loading", font=("Arial", 13, "italic"), foreground="#55D5E0")

# Lier le clic sur les URLs
output_box.tag_bind("url", "<Button-1>", lambda e: open_url(output_box, e))
output_box.tag_bind("url", "<Enter>", lambda e: output_box.config(cursor="hand2"))
output_box.tag_bind("url", "<Leave>", lambda e: output_box.config(cursor=""))

# Bind Enter key pour la recherche
question_entry.bind("<Return>", lambda e: on_send())

app.mainloop()