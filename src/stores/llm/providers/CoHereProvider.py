from ...llm import LLMInterface, CohereEnums, DocTypeEnums
import cohere
import logging


class CoHereProvider(LLMInterface):
    def __init__(
        self,
        api_key: str,
        default_input_max_characters: int = 1000,
        default_output_max_tokens: int = 1000,
        default_temperature: float = 0.1,
    ):
        self.api_key = api_key

        self.default_input_max_characters = default_input_max_characters
        self.default_output_max_tokens = default_output_max_tokens
        self.default_temperature = default_temperature

        self.generation_model_id = None

        self.embedding_model_id = None
        self.embedding_size = None

        self.client = cohere.ClientV2(
            api_key=self.api_key,
        )

        self.logger = logging.getLogger(__name__)

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
            self.logger.error("OpenAI client is not initialized.")
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
            messages = [self.construct_prompt(prompt, CohereEnums.USER.value)]
        else:
            messages = chat_history + [
                self.construct_prompt(prompt, CohereEnums.USER.value)
            ]

        response = self.client.chat(
            model=self.generation_model_id,
            messages=messages,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )

        # validate the response and its output
        if (
            not response
            or not response.message
            or not response.message.content
            or len(response.message.content) == 0
            or not response.message.content[0].text
        ):
            self.logger.error("Error while generating text with CoHere API.")
            return None
        return response.message.content[0].text

    def embed_text(self, text: str, doc_type: str = None) -> list[float] | None:
        # validate the client is initialized
        if not self.client:
            # raise ValueError("OpenAI client is not initialized.")
            self.logger.error("CoHere client is not initialized.")
            return None
        # validate the embedding model is set
        if not self.embedding_model_id:
            # raise ValueError("Embedding model is not set.")
            self.logger.error("Embedding model is not set.")
            return None

        input_type = CohereEnums.DOCUMENT.value
        if doc_type == DocTypeEnums.QUERY.value:
            input_type = CohereEnums.QUERY.value

        response = self.client.embed(
            model=self.embedding_model_id,
            texts=[self.process_text(text)],
            input_type=input_type,
            embedding_types=["float"],
        )
        # validate the response and its data
        if (
            not response
            or not response.embeddings
            or not response.embeddings.float
            or len(response.embeddings.float) == 0
            or not response.embeddings.float[0]
        ):
            self.logger.error("Error while embedding text with CoHere.")
            return None

        return response.embeddings.float[0]

    def construct_prompt(self, prompt: str, role: str):
        return {
            "role": role,
            "content": self.process_text(prompt),
        }
