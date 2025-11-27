"""
Sistema de Internacionalização (i18n) para TaskAutoGUI
Suporta múltiplos idiomas através de arquivos JSON
"""
import json
import os
from pathlib import Path


class I18n:
    """Gerenciador de traduções"""
    
    def __init__(self, language='pt'):
        """
        Inicializa o sistema de tradução
        
        Args:
            language: Código do idioma (pt, en, es, etc.)
        """
        self.language = language
        self.translations = {}
        self.fallback_language = 'pt'  # Idioma padrão se tradução faltar
        self.load_translations()
    
    def _get_lang_file(self, lang):
        """Retorna o caminho do arquivo de tradução"""
        script_dir = Path(__file__).parent.absolute()
        lang_file = script_dir / "locales" / f"{lang}.json"
        return lang_file
    
    def load_translations(self):
        """Carrega as traduções do arquivo JSON"""
        lang_file = self._get_lang_file(self.language)
        
        # Tenta carregar o idioma solicitado
        if lang_file.exists():
            try:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    self.translations = json.load(f)
                return
            except Exception as e:
                print(f"⚠️ Erro ao carregar traduções {self.language}: {e}")
        
        # Se falhar, tenta carregar o idioma de fallback
        if self.language != self.fallback_language:
            fallback_file = self._get_lang_file(self.fallback_language)
            if fallback_file.exists():
                try:
                    with open(fallback_file, 'r', encoding='utf-8') as f:
                        self.translations = json.load(f)
                    print(f"⚠️ Usando idioma de fallback: {self.fallback_language}")
                    return
                except Exception as e:
                    print(f"⚠️ Erro ao carregar traduções de fallback: {e}")
        
        # Se tudo falhar, usa traduções vazias (retornará as chaves)
        self.translations = {}
        print(f"⚠️ Nenhuma tradução encontrada. Usando chaves como texto.")
    
    def set_language(self, language):
        """Altera o idioma e recarrega as traduções"""
        self.language = language
        self.load_translations()
    
    def get_available_languages(self):
        """Retorna lista de idiomas disponíveis"""
        locales_dir = Path(__file__).parent.absolute() / "locales"
        if not locales_dir.exists():
            return []
        
        languages = []
        for lang_file in locales_dir.glob("*.json"):
            languages.append(lang_file.stem)
        return sorted(languages)
    
    def t(self, key, **kwargs):
        """
        Traduz uma chave
        
        Args:
            key: Chave de tradução (pode usar notação de ponto para aninhamento, ex: 'messages.recording')
            **kwargs: Variáveis para substituir no texto (ex: {'count': 5})
        
        Returns:
            String traduzida ou a própria chave se não encontrada
        """
        # Suporta notação de ponto para chaves aninhadas
        keys = key.split('.')
        value = self.translations
        
        try:
            for k in keys:
                value = value[k]
        except (KeyError, TypeError):
            # Se não encontrar, tenta no idioma de fallback
            if self.language != self.fallback_language:
                fallback_file = self._get_lang_file(self.fallback_language)
                if fallback_file.exists():
                    try:
                        with open(fallback_file, 'r', encoding='utf-8') as f:
                            fallback_translations = json.load(f)
                            value = fallback_translations
                            for k in keys:
                                value = value[k]
                    except:
                        return key  # Retorna a chave se não encontrar em lugar nenhum
                else:
                    return key
            else:
                return key
        
        # Se o valor for uma string, substitui variáveis
        if isinstance(value, str):
            try:
                return value.format(**kwargs)
            except KeyError:
                # Se faltar alguma variável, retorna o texto sem substituição
                return value
        else:
            return str(value)
    
    def __call__(self, key, **kwargs):
        """Permite usar i18n('key') em vez de i18n.t('key')"""
        return self.t(key, **kwargs)


# Instância global do i18n
_i18n_instance = None


def get_i18n(language=None):
    """
    Obtém ou cria a instância global do i18n
    
    Args:
        language: Se fornecido, define o idioma. Se None, retorna a instância atual
    
    Returns:
        Instância do I18n
    """
    global _i18n_instance
    
    if _i18n_instance is None:
        # Tenta carregar idioma do arquivo de configuração
        config_lang = _load_language_from_config()
        _i18n_instance = I18n(config_lang)
    elif language is not None:
        _i18n_instance.set_language(language)
    
    return _i18n_instance


def _load_language_from_config():
    """Carrega o idioma do arquivo de configuração"""
    config_file = Path(__file__).parent.absolute() / "config.json"
    
    if config_file.exists():
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('language', 'pt')
        except:
            pass
    
    # Tenta detectar idioma do sistema
    try:
        import locale
        system_lang = locale.getdefaultlocale()[0]
        if system_lang:
            # Converte código de locale para código de idioma simples
            lang_code = system_lang.split('_')[0].lower()
            # Verifica se o idioma está disponível
            locales_dir = Path(__file__).parent.absolute() / "locales"
            if locales_dir.exists() and (locales_dir / f"{lang_code}.json").exists():
                return lang_code
    except:
        pass
    
    return 'pt'  # Padrão


def set_language(language):
    """Define o idioma global"""
    get_i18n(language)


# Função de conveniência para tradução rápida
def t(key, **kwargs):
    """Traduz uma chave usando a instância global"""
    return get_i18n().t(key, **kwargs)

