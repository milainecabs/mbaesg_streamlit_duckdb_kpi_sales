# utils.py
import locale

try:
    locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
except:
    locale.setlocale(locale.LC_ALL, 'French_France')

def format_fr(x):
    try:
        return locale.format_string("%d", int(x), grouping=True)
    except:
        return x
