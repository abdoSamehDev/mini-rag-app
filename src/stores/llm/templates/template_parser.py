import os


class TemplateParser:
    def __init__(self, language: str = None, default_language: str = "en"):
        self.current_dir_path = os.path.dirname(
            os.path.abspath(__file__)
        )  # get templates dir path
        self.default_language = default_language
        self.language = language

        self.set_language(language)

    def set_language(self, language: str):
        # this method to help us setting/changing lang on the run time instead of setting it once at te begging
        if not language:
            self.language = self.default_language
        language_path = os.path.join(self.current_dir_path, "locales", language)
        if os.path.exists(language_path):
            self.language = language
        else:
            self.language = self.default_language

    def get(self, group: str, key: str, vars: dict = {}):
        if not group or not key:
            return None

        targeted_language = self.language
        group_path = os.path.join(
            self.current_dir_path, "locales", targeted_language, f"{group}.py"
        )
        if not os.path.exists(group_path):
            targeted_language = self.default_language
            group_path = os.path.join(
                self.current_dir_path, "locales", targeted_language, f"{group}.py"
            )

        # import group module
        module = __import__(
            f"store.llm.templates.locales.{targeted_language}.{group}", fromlist=[group]
        )
        # __import_() is Python's built-in dynamic importer as the importing path has variables, so we build the import at the run time
        # ex: lang is en, so this is eq to:
        # from stores.llm.templates.locales.en import rag

        if not module:
            return None
        key_attribute = getattr(module, key)
        # same ex + key is "system_prompt":
        # key_attribute = rag.system_prompts
        return key_attribute.substitute(vars)
        # string.Template replaces all placeholders with the vars dict
