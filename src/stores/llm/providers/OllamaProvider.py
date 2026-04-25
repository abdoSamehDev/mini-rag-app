from ...llm import LLMInterface, OpenAIEnums
from ollama import Client
from helpers import get_logger


class OllamaProvider(LLMInterface):
    def __init__(
        self,
        api_key: str,
        api_url: str = None,
        default_input_max_characters: int = 1000,
        default_output_max_tokens: int = 1000,
        default_temperature: float = 0.1,
    ):
        self.api_key = api_key
        self.api_url = api_url

        self.default_input_max_characters = default_input_max_characters
        self.default_output_max_tokens = default_output_max_tokens
        self.default_temperature = default_temperature

        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None

        self.client = Client(host=self.api_url)

        self.logger = get_logger()

    def process_text(self, text: str):
        return text[: self.default_input_max_characters].strip()

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def set_embedding_model(self, model_id: str, embedding_size: int):
        self.embedding_model_id = model_id
        self.embedding_size = embedding_size

    def generate_text(
        self,
        prompt: str,
        chat_history: list = [],
        max_output_tokens: int = None,
        temperature: float = None,
    ):
        # # if we dont need to use a method in the provider class, but we have to use it as it's in the interface, we call it with no logic, but only using raise.
        # raise NotImplementedError(
        #     "This method is not implemented for OpenAIProvider. Use the OpenAI API directly for text generation."
        # )
        # validate the client is initialized
        if not self.client:
            # raise ValueError("OpenAI client is not initialized.")
            self.logger.error("OLLAMA client is not initialized.")
            return None
        # validate the generation model is set
        if not self.generation_model_id:
            # raise ValueError("Generation model is not set.")
            self.logger.error("Generation model is not set.")
            return None

        max_output_tokens = (
            max_output_tokens if max_output_tokens else self.default_output_max_tokens
        )
        temperature = temperature if temperature else self.default_temperature

        if not chat_history or len(chat_history) == 0:
            messages = [self.construct_prompt(prompt, OpenAIEnums.USER.value)]
        else:
            messages = chat_history + [
                self.construct_prompt(prompt, OpenAIEnums.USER.value)
            ]

        # FOR OLLAMA WITH OLLAMA CLIENT (LOCAL MODELS)
        response = self.client.chat(
            model=self.generation_model_id,
            messages=messages,
            options={"temperature": temperature},
            think=False,
        )

        # validate the response and its output
        if not response or not response.message or not response.message.content:
            self.logger.error("Error while generating text with OLLAMA CLIENT.")
            return None

        # FOR OLLAMA WITH OLLAMA CLIENT (LOCAL MODELS)
        return response.message.content

    def embed_text(
        self, text: str | list[str], doc_type: str = None
    ) -> list[float] | None:
        # validate the client is initialized
        if not self.client:
            # raise ValueError("OpenAI client is not initialized.")
            self.logger.error("OLLAMA client is not initialized.")
            return None
        # validate the embedding model is set
        if not self.embedding_model_id:
            # raise ValueError("Embedding model is not set.")
            self.logger.error("Embedding model is not set.")
            return None

        if isinstance(text, str):
            text = [text]

        response = self.client.embed(
            model=self.embedding_model_id,
            input=text,
        )
        # validate the response and its data
        if not response or not response.embeddings or len(response.embeddings) == 0:
            self.logger.error("Error while embedding text with Ollama.")
            return None

        return response.embeddings

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": prompt,
        }
