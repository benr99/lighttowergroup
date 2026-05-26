"""
Fetch brand colors from the deployed lighttowergroup.co site CSS.
Falls back to hardcoded values if the site is unreachable.
"""

import requests
import re
import logging

logger = logging.getLogger(__name__)

FALLBACK_COLORS = {
    'bg_primary': '#0A0A0A',        # Near-black — covers, transitions
    'bg_page': '#0F0F0D',           # Dark — body pages
    'bg_light': '#F8F6F1',          # Warm off-white — alternating pages
    'text_primary': '#F5F5F0',      # Off-white on dark
    'text_on_light': '#1A1A16',     # Near-black on light
    'text_muted_dark': '#8A8A80',   # Muted gray on dark
    'text_muted_light': '#6A6A60',  # Muted gray on light
    'accent_gold': '#C9A84C',       # BRAND ACCENT (from site.css :root)
    'accent_gold_light': '#E8D4A8', # Pale gold for dividers
    'rule_dark': '#2C2C28',         # Hairline on dark
    'rule_light': '#D8D5CE',        # Hairline on light
}

def fetch_brand_colors() -> dict:
    """
    Read :root CSS variables from deployed lighttowergroup.co.
    Returns actual brand colors. Falls back to hardcoded if unreachable.
    """
    colors = FALLBACK_COLORS.copy()

    try:
        response = requests.get('https://lighttowergroup.co', timeout=5)
        if response.status_code == 200:
            # Look for :root { ... } block
            root_match = re.search(r':root\s*\{([^}]+)\}', response.text, re.DOTALL)
            if root_match:
                root_css = root_match.group(1)

                # Extract --accent-gold (most critical brand color)
                gold_match = re.search(r'--brand-accent:\s*([#\w]+)', root_css)
                if gold_match:
                    colors['accent_gold'] = gold_match.group(1)
                    logger.info(f"Fetched accent gold from live CSS: {colors['accent_gold']}")

                # Extract other colors if present
                color_vars = {
                    '--bg-primary': 'bg_primary',
                    '--bg-page': 'bg_page',
                    '--bg-light': 'bg_light',
                    '--text-primary': 'text_primary',
                    '--text-on-light': 'text_on_light',
                }

                for css_var, key in color_vars.items():
                    var_match = re.search(rf'{css_var}:\s*([#\w]+)', root_css)
                    if var_match:
                        colors[key] = var_match.group(1)

    except requests.exceptions.RequestException as e:
        logger.warning(f"Could not fetch colors from live site: {e}. Using fallback.")
    except Exception as e:
        logger.error(f"Error parsing brand colors: {e}")

    return colors

if __name__ == '__main__':
    import json
    colors = fetch_brand_colors()
    print(json.dumps(colors, indent=2))
