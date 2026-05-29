from abc import ABC, abstractmethod

from pregnancy_copilot.models import MessageEvent


class MessageAdapter(ABC):
    @abstractmethod
    def receive_message(self, payload: dict) -> MessageEvent:
        raise NotImplementedError

    @abstractmethod
    def send_reply(self, message: MessageEvent, text: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def write_doc(self, title: str, content: str) -> str:
        raise NotImplementedError
