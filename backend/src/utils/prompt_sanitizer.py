"""
Prompt Sanitizer
=================

Utilitaires de validation et sanitization des prompts système
pour prévenir les attaques par injection.
"""

import re

# Patterns dangereux à bloquer
DANGEROUS_PATTERNS = [
    # Tentatives d'injection de rôle
    r"(?i)ignore\s+(all\s+)?previous\s+instructions?",
    r"(?i)forget\s+(all\s+)?previous\s+instructions?",
    r"(?i)disregard\s+(all\s+)?previous",
    r"(?i)you\s+are\s+now\s+a?\s*(new|different)",
    r"(?i)new\s+role\s*:",
    r"(?i)system\s*:\s*you\s+are",
    # Tentatives d'extraction de prompt
    r"(?i)reveal\s+(your\s+)?system\s+prompt",
    r"(?i)show\s+(me\s+)?(your\s+)?instructions?",
    r"(?i)what\s+(are|is)\s+(your\s+)?system\s+(prompt|instruction)",
    r"(?i)print\s+(your\s+)?prompt",
    # Caractères de contrôle dangereux
    r"[\x00-\x08\x0b\x0c\x0e-\x1f]",
    # Tentatives de markdown/HTML injection
    r"<script[^>]*>",
    r"javascript\s*:",
    r"data\s*:\s*text/html",
]

# Mots-clés suspects (warning, pas blocage)
SUSPICIOUS_KEYWORDS = [
    "jailbreak",
    "DAN",
    "developer mode",
    "pretend you",
    "act as if",
    "roleplay as",
    "ignore safety",
    "bypass",
]


def sanitize_system_prompt(prompt: str) -> str:
    """
    Sanitize un prompt système en supprimant les caractères dangereux.

    Args:
        prompt: Le prompt à sanitizer

    Returns:
        Le prompt nettoyé
    """
    if not prompt:
        return prompt

    # Supprimer les caractères de contrôle (sauf newline, tab)
    sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", prompt)

    # Normaliser les espaces multiples
    sanitized = re.sub(r"[ \t]+", " ", sanitized)

    # Limiter les newlines consécutifs
    sanitized = re.sub(r"\n{4,}", "\n\n\n", sanitized)

    # Supprimer les balises script
    sanitized = re.sub(r"<script[^>]*>.*?</script>", "", sanitized, flags=re.IGNORECASE | re.DOTALL)

    # Supprimer les URLs javascript:
    sanitized = re.sub(r"javascript\s*:", "", sanitized, flags=re.IGNORECASE)

    return sanitized.strip()


def validate_prompt_length(prompt: str, max_length: int = 4000) -> tuple[bool, str]:
    """
    Valide la longueur d'un prompt.

    Args:
        prompt: Le prompt à valider
        max_length: Longueur maximale autorisée

    Returns:
        (valid, error_message)
    """
    if not prompt:
        return True, ""

    if len(prompt) > max_length:
        return (
            False,
            f"System prompt exceeds maximum length of {max_length} characters (got {len(prompt)})",
        )

    return True, ""


def detect_injection_attempt(prompt: str) -> tuple[bool, str, list[str]]:
    """
    Détecte les tentatives d'injection dans un prompt.

    Args:
        prompt: Le prompt à analyser

    Returns:
        (is_dangerous, severity, matched_patterns)
        severity: "blocked" ou "warning"
    """
    if not prompt:
        return False, "", []

    matched = []

    # Vérifier les patterns dangereux
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, prompt):
            matched.append(pattern)

    if matched:
        return True, "blocked", matched

    # Vérifier les mots-clés suspects
    lower_prompt = prompt.lower()
    suspicious_found = [kw for kw in SUSPICIOUS_KEYWORDS if kw.lower() in lower_prompt]

    if suspicious_found:
        return True, "warning", suspicious_found

    return False, "", []


def validate_system_prompt(
    prompt: str, max_length: int = 4000, block_injection: bool = True
) -> tuple[bool, str | None, str]:
    """
    Validation complète d'un prompt système.

    Args:
        prompt: Le prompt à valider
        max_length: Longueur maximale
        block_injection: Si True, bloque les injections détectées

    Returns:
        (valid, error_message, sanitized_prompt)
    """
    if not prompt:
        return True, None, ""

    # 1. Sanitization de base
    sanitized = sanitize_system_prompt(prompt)

    # 2. Validation longueur
    valid, error = validate_prompt_length(sanitized, max_length)
    if not valid:
        return False, error, sanitized

    # 3. Détection d'injection
    is_dangerous, severity, patterns = detect_injection_attempt(sanitized)

    if is_dangerous and severity == "blocked" and block_injection:
        return False, "Potential prompt injection detected. Blocked patterns found.", sanitized

    # Warning logged mais pas bloqué
    if is_dangerous and severity == "warning":
        # On pourrait logger ici
        pass

    return True, None, sanitized


# ============================================
# Rate limiting pour prompts longs
# ============================================


def estimate_prompt_tokens(prompt: str) -> int:
    """
    Estime le nombre de tokens d'un prompt (approximation).

    Règle approximative: 1 token ≈ 4 caractères en anglais,
    3 caractères en français/autres langues latines.
    """
    if not prompt:
        return 0

    # Utiliser une moyenne de 3.5 caractères par token
    return len(prompt) // 4 + 1


def check_prompt_complexity(prompt: str) -> dict:
    """
    Analyse la complexité d'un prompt.

    Returns:
        {
            "length": int,
            "estimated_tokens": int,
            "newlines": int,
            "has_code": bool,
            "complexity_score": int  # 1-10
        }
    """
    if not prompt:
        return {
            "length": 0,
            "estimated_tokens": 0,
            "newlines": 0,
            "has_code": False,
            "complexity_score": 1,
        }

    length = len(prompt)
    newlines = prompt.count("\n")
    has_code = bool(re.search(r"```|def |class |function |const |let |var ", prompt))
    estimated_tokens = estimate_prompt_tokens(prompt)

    # Score de complexité
    score = 1
    if length > 500:
        score += 1
    if length > 1000:
        score += 1
    if length > 2000:
        score += 2
    if newlines > 10:
        score += 1
    if newlines > 30:
        score += 1
    if has_code:
        score += 2
    if estimated_tokens > 500:
        score += 1

    return {
        "length": length,
        "estimated_tokens": estimated_tokens,
        "newlines": newlines,
        "has_code": has_code,
        "complexity_score": min(10, score),
    }
