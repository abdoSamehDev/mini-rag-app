from llm import LLMInterface, OpenAIEnums
from openai import OpenAI
import logging


class OpenAIProvider(LLMInterface):
    def __init__(
        self,
        api_key: str,
        api_url: str = None,  # Not used for OpenAI, but with dealing with other providers through OpenAI API.
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

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_url,
        )

        self.logger = logging.getLogger(__name__)

    def proces_text(self, text: str):
        return text[: self.default_input_max_characters].strip()

    def set_generation_model(self, model_id: str):
        self.generation_model_id = model_id

    def generate_embedding_model(self, model_id: str, embedding_size: int):
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
            message = self.proces_text(prompt)
        else:
            message = chat_history + [
                {
                    "role": OpenAIEnums.USER.value,
                    "content": self.proces_text(prompt),
                }
            ]

        response = self.client.responses.create(
            model=self.generation_model_id,
            input=message,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
        )

        # validate the response and its output
        if not response or not response.output_text:
            self.logger.error("Error while generating text with OpenAI API.")
            return None
        return response.output_text

        # chat_history.append(self.construct_prompt(prompt, OpenAIRolesEnum.USER.value))

        # response = self.client.chat.completions.create(
        #     model=self.generation_model_id,
        #     messages=chat_history,
        #     max_tokens=max_output_tokens,
        #     temperature=temperature,
        # )
        # if (
        #     not response
        #     or not response.choices
        #     or len(response.choices) == 0
        #     or not response.choices[0].message
        # ):
        #     self.logger.error("Error while generating text with OpenAI API.")
        #     return None
        # return response.choices[0].message["content"]

    def embed_text(self, text: str, doc_type: str = None):
        # validate the client is initialized
        if not self.client:
            # raise ValueError("OpenAI client is not initialized.")
            self.logger.error("OpenAI client is not initialized.")
            return None
        # validate the embedding model is set
        if not self.embedding_model_id:
            # raise ValueError("Embedding model is not set.")
            self.logger.error("Embedding model is not set.")
            return None

        response = self.client.embeddings.create(
            input=text,
            model=self.embedding_model_id,
        )
        # validate the response and its data
        if (
            not response
            or not response.data
            or len(response.data) == 0
            or not response.data[0].embedding
        ):
            self.logger.error("Error while embedding text with OpenAI API.")
            return None

        return response.data[0].embedding

    def construct_prompt(self, prompt: str, role: str):
        # we are using the new OpenAI method (Response API) rather than the old one (Chat Completions) so no need to construct the prompt.
        raise NotImplementedError(
            "construct_prompt is not needed for OpenAIProvider. "
            "Message formatting is handled internally by generate_text."
        )
