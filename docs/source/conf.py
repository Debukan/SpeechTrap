# Configuration file for the Sphinx documentation builder.

# -- Project information -----------------------------------------------------
project = 'SpeechTrap'
copyright = '2025, Our Team'
author = 'Our Team'
release = '0.1'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',      # Для Google-style docstrings
    'sphinx.ext.viewcode',
    'sphinxcontrib.httpdomain'  # Для HTTP API документации
]

templates_path = ['_templates']
exclude_patterns = []
language = 'ru'

# -- Настройки автодокументирования ------------------------------------------
autodoc_default_options = {
    'members': True,
    'show-inheritance': True
}

# -- Путь к проекту ---------------------------------------------------------
import os
import sys
sys.path.insert(0, os.path.abspath('docs/source/api'))

# -- HTML настройки ---------------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']