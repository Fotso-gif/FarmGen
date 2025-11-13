from PIL import Image
import pytesseract
import re
import numpy as np
import os

# Configuration Tesseract
try:
    pytesseract.pytesseract.tesseract_cmd = r"../Tesseract-OCR/tesseract.exe"
except:
    pass  # Utiliser le chemin par défaut sur Linux/Mac

def find_first_match(patterns, texte, group=1):
    """Cherche la première correspondance parmi plusieurs regex."""
    for pattern in patterns:
        match = re.search(pattern, texte, re.IGNORECASE)
        if match:
            return match.group(group)
    return None

def process_payment_capture(image_path):
    """Traite une capture d'écran et extrait les données de paiement."""
    try:
        # Ouvrir et prétraiter l'image
        image = Image.open(image_path)
        
        # OCR sur l'image
        texte = pytesseract.image_to_string(image, lang='eng+fra')
        
        # Patterns pour extraction des données
        patterns_montant = [
            r"transferred\s+([\d,]+)\s+XAF",
            r"transaction\s+of\s+([\d,]+)\s+XAF",
            r"montant\s*:\s*([\d,]+)\s*XAF",
            r"amount\s*:\s*([\d,]+)\s*XAF",
            r"([\d,]+)\s+XAF\s+transféré",
            r"([\d,]+)\s+XAF\s+paid"
        ]
        
        data = {}
        
        # Montant transféré
        montant = find_first_match(patterns_montant, texte)
        if montant:
            data["montant"] = float(montant.replace(',', ''))
        
        # Nom du destinataire
        match = re.search(r"to\s+([A-Z\s]+)\(", texte, re.IGNORECASE)
        if not match:
            match = re.search(r"destinataire\s*:\s*([A-Z\s]+)", texte, re.IGNORECASE)
        if match:
            data["destinataire"] = match.group(1).strip()
        
        # Numéro destinataire
        match = re.search(r"\((\d{9,12})\)", texte)
        if not match:
            match = re.search(r"numero\s*:\s*(\d{9,12})", texte, re.IGNORECASE)
        if match:
            data["numero_destinataire"] = match.group(1)
        
        # Date et heure
        match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})", texte)
        if not match:
            match = re.search(r"(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})", texte)
        if match:
            data["date_heure"] = match.group(1)
        
        # Transaction ID
        match = re.search(r"transaction\s+id\s*:\s*(\d+)", texte, re.IGNORECASE)
        if not match:
            match = re.search(r"reference\s*:\s*(\d+)", texte, re.IGNORECASE)
        if match:
            data["transaction_id"] = match.group(1)
        
        # Nouveau solde
        match = re.search(r"balance\s*:\s*([\d,]+)\s*XAF", texte, re.IGNORECASE)
        if match:
            data["solde"] = float(match.group(1).replace(',', ''))
        
        # Texte complet pour debug
        data["texte_complet"] = texte[:500] + "..." if len(texte) > 500 else texte
        
        return data
        
    except Exception as e:
        return {"erreur": str(e)}